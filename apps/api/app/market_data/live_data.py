"""Real market data for the owner's private staging (ADR-027).

Only providers the owner listed in MARKET_PULSE_REAL_DATA_PROVIDERS, with their credential
present, are called, in the registry's precedence. Each answer comes from one provider; a
fallback is recorded, never blended. Values are cached in Redis (in the process when Redis is
down) to stay inside each plan's quota, and every call goes through a per-provider budget and
cooldown. A failed refresh serves the last validated value as STALE; with nothing validated
the answer is UNAVAILABLE with its reason. Nothing here is DEMO and nothing is filled in: an
unknown change stays None and an absent timestamp stays absent.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from app.core.config import get_settings
from app.core.redis_client import shared_redis
from app.market_data.normalization import AdjustmentType, MarketBar
from app.market_data.quality import check_series
from app.providers import vendors
from app.providers.canonical import (
    CanonicalFxRate,
    CanonicalQuote,
    NormalizationError,
    QualityStatus,
    UnavailableReason,
)
from app.providers.http import ProviderHttpTransport
from app.providers.models import DataLevel, Freshness, ProviderCapability
from app.providers.precedence import serve
from app.providers.registry import (
    PRECEDENCE,
    ActivationDecision,
    ProviderRegistryEntry,
    get_entry,
    owner_use_decision,
)
from app.providers.resilience import CircuitBreaker, RetryPolicy, backoff_delay
from app.providers.vendors import InstrumentRef, SeriesResult

LOGGER = logging.getLogger("market_pulse.live_data")

PRIVATE_USE_NOTE = (
    "Uso privado do responsável no staging (ADR-027): a licença pública desta fonte não foi "
    "aprovada."
)


@dataclass(frozen=True)
class LiveInstrument:
    canonical_id: str
    market: str  # BR, US or FX: the key into the registry's precedence
    currency: str
    timezone: str
    symbols: Mapping[str, str]  # provider id -> that provider's symbol


_BR, _US = "America/Sao_Paulo", "America/New_York"

# The instruments with a verified normalizer for at least one approved provider. Anything
# else (S&P 500, Nasdaq, CDI, IPCA, IFIX, BTC) stays UNAVAILABLE in real mode.
LIVE_INSTRUMENTS: Mapping[str, LiveInstrument] = {
    item.canonical_id: item
    for item in (
        LiveInstrument("equity.br.b3.petr4", "BR", "BRL", _BR, {"brapi": "PETR4"}),
        LiveInstrument("index.br.b3.ibovespa", "BR", "BRL", _BR, {"brapi": "^BVSP"}),
        LiveInstrument(
            "equity.us.nasdaq.aapl",
            "US",
            "USD",
            _US,
            {"twelve_data": "AAPL", "massive": "AAPL", "alpha_vantage": "AAPL"},
        ),
        LiveInstrument("fx.global.usd-brl", "FX", "BRL", "UTC", {"open_exchange_rates": "USD"}),
    )
}

# Conservative levels for the free plans described in the registry; never REAL_TIME.
PLAN_LEVEL: Mapping[str, DataLevel] = {
    "brapi": DataLevel.DELAYED,
    "twelve_data": DataLevel.DELAYED,
    "massive": DataLevel.EOD,
    "alpha_vantage": DataLevel.EOD,
    "open_exchange_rates": DataLevel.DELAYED,
}

METHODOLOGY: Mapping[str, str] = {
    "brapi": "brapi: cotação com atraso; o plano gratuito atualiza a cada 30 minutos.",
    "twelve_data": (
        "Twelve Data: último candle diário; não é tempo real e o atraso depende do plano."
    ),
    "massive": "Massive: barras diárias de fim de pregão, sem ajuste.",
    "alpha_vantage": "Alpha Vantage: GLOBAL_QUOTE do fim do pregão; moeda tomada do catálogo.",
    "open_exchange_rates": (
        "Open Exchange Rates: base USD, atualizada de hora em hora no plano gratuito."
    ),
}

DATASETS: Mapping[tuple[str, str], str] = {
    ("brapi", "quote"): "brapi.v2.stocks.quote",
    ("brapi", "series"): "brapi.v2.stocks.historical.raw",
    ("twelve_data", "quote"): "twelve_data.quote",
    ("twelve_data", "series"): "twelve_data.time_series.1day.unadjusted",
    ("massive", "quote"): "massive.aggs.1day.unadjusted.last_close",
    ("massive", "series"): "massive.aggs.1day.unadjusted",
    ("alpha_vantage", "quote"): "alpha_vantage.global_quote",
    ("open_exchange_rates", "fx"): "open_exchange_rates.latest",
}

# Seconds a value counts as FRESH, then how long it may still be served as STALE.
FRESH_SECONDS: Mapping[str, int] = {
    "brapi": 30 * 60,
    "twelve_data": 15 * 60,
    "massive": 6 * 3600,
    "alpha_vantage": 3600,
    "open_exchange_rates": 3600,
}
SERIES_FRESH_SECONDS = 6 * 3600
STALE_SECONDS = 7 * 24 * 3600

# Calls per minute and per UTC day, kept under each free plan's documented limit.
BUDGETS: Mapping[str, tuple[int | None, int | None]] = {
    "brapi": (None, 450),  # 15.000 per month
    "twelve_data": (7, 700),  # 8 per minute, 800 per day
    "alpha_vantage": (None, 20),  # 25 per day
    "open_exchange_rates": (None, 30),  # 1.000 per month
    "massive": (4, None),  # 5 per minute
}

RETRY = RetryPolicy(max_attempts=2, base_delay_seconds=0.5, max_delay_seconds=1.0)
TIMEOUT_SECONDS = 8.0
# Provider-wide pauses: a rejected key, a rate limit or a failing source.
COOLDOWN_SECONDS = {"rate_limited": 300, "rejected": 3600, "source": 60}
# A refusal of one query (outside the plan, unreadable payload) pauses only that query.
REMEMBERED_REFUSALS = frozenset(
    {UnavailableReason.LICENSE_BLOCKED, UnavailableReason.SCHEMA_UNSUPPORTED}
)
REFUSED_SECONDS = 3600

# Normalizers that exist, per (provider, kind). A provider without one is skipped, not guessed.
_IMPLEMENTED = {
    "quote": ("brapi", "twelve_data", "massive", "alpha_vantage"),
    "series": ("brapi", "twelve_data", "massive"),
    "fx": ("open_exchange_rates",),
}


# --- Storage: Redis first, the process as fallback ------------------------------------------


class _Store:
    def __init__(self) -> None:
        self._memory: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _client():
        settings = get_settings()
        return shared_redis(settings.redis_url, settings.cache_timeout_seconds)

    def get(self, key: str) -> str | None:
        try:
            return self._client().get(key)
        except Exception:
            with self._lock:
                item = self._memory.get(key)
                if item is None or item[1] <= time.monotonic():
                    self._memory.pop(key, None)
                    return None
                return item[0]

    def set(self, key: str, value: str, ttl: int) -> None:
        try:
            self._client().set(key, value, ex=max(1, ttl))
        except Exception:
            with self._lock:
                self._memory[key] = (value, time.monotonic() + max(1, ttl))

    def incr(self, key: str, ttl: int) -> int:
        try:
            client = self._client()
            count = int(client.incr(key))
            if count == 1:
                client.expire(key, ttl)
            return count
        except Exception:
            with self._lock:
                value, expires = self._memory.get(key, ("0", time.monotonic() + ttl))
                count = int(value) + 1
                self._memory[key] = (str(count), expires)
                return count

    def clear_memory(self) -> None:
        with self._lock:
            self._memory.clear()


STORE = _Store()
_BREAKERS: dict[str, CircuitBreaker] = {}
_KEY_LOCKS: dict[str, threading.Lock] = {}
_GUARD = threading.Lock()
# Replaced in tests; production uses urllib.
OPENER: list[Callable[..., Any] | None] = [None]


def _key(*parts: str) -> str:
    return "market_data:live:" + ":".join(parts)


def _key_lock(key: str) -> threading.Lock:
    with _GUARD:
        return _KEY_LOCKS.setdefault(key, threading.Lock())


def _breaker(provider_id: str) -> CircuitBreaker:
    with _GUARD:
        return _BREAKERS.setdefault(
            provider_id, CircuitBreaker(failure_threshold=3, cooldown_seconds=300)
        )


def reset_state() -> None:
    """Tests only: forget breakers and in-process values."""

    with _GUARD:
        _BREAKERS.clear()
    STORE.clear_memory()


# --- Activation, budget and cooldown --------------------------------------------------------


def approved_providers() -> frozenset[str]:
    return frozenset(get_settings().real_data_providers)


def real_data_enabled() -> bool:
    return bool(get_settings().real_data_providers)


def _owner_decision(
    entry: ProviderRegistryEntry, environ: Mapping[str, str] | None = None
) -> ActivationDecision:
    return owner_use_decision(entry, environ, approved=approved_providers())


def _decide(entry: ProviderRegistryEntry, environ: Mapping[str, str] | None = None):
    decision = _owner_decision(entry, environ)
    if not decision.allowed:
        return decision
    cooldown = STORE.get(_key("cooldown", entry.provider_id))
    if cooldown:
        try:
            reason = UnavailableReason(cooldown)
        except ValueError:
            reason = UnavailableReason.RATE_LIMITED
        return ActivationDecision(False, reason)
    if not _budget_left(entry.provider_id):
        return ActivationDecision(False, UnavailableReason.RATE_LIMITED)
    return decision


def _budget_keys(provider_id: str, now: datetime) -> tuple[str, str]:
    return (
        _key("budget", provider_id, "minute", now.strftime("%Y%m%d%H%M")),
        _key("budget", provider_id, "day", now.strftime("%Y%m%d")),
    )


def _budget_left(provider_id: str) -> bool:
    per_minute, per_day = BUDGETS.get(provider_id, (None, None))
    minute_key, day_key = _budget_keys(provider_id, datetime.now(UTC))
    for limit, key in ((per_minute, minute_key), (per_day, day_key)):
        if limit is not None and int(STORE.get(key) or 0) >= limit:
            return False
    return True


def _spend_budget(provider_id: str) -> None:
    minute_key, day_key = _budget_keys(provider_id, datetime.now(UTC))
    STORE.incr(minute_key, 120)
    STORE.incr(day_key, 2 * 24 * 3600)


def credential_rejected(provider_id: str) -> bool:
    """True when the provider answered 401 to the configured credential (status INVÁLIDA)."""

    return bool(STORE.get(_key("rejected", provider_id)))


def _cool_down(provider_id: str, reason: UnavailableReason, seconds: float) -> None:
    STORE.set(_key("cooldown", provider_id), reason.value, int(max(1, seconds)))


def _send(provider_id: str, request: vendors.ProviderRequest) -> Any:
    entry = get_entry(provider_id)
    kwargs: dict[str, Any] = {"timeout_seconds": TIMEOUT_SECONDS, "authorize": _owner_decision}
    if OPENER[0] is not None:
        kwargs["opener"] = OPENER[0]
    transport = ProviderHttpTransport(entry, os.environ, **kwargs)
    for attempt in range(RETRY.max_attempts):
        _spend_budget(provider_id)
        try:
            payload = transport.send(request).payload
        except NormalizationError as error:
            status = error.http_status
            LOGGER.warning(
                "live_provider_error",
                extra={"provider": provider_id, "reason": error.reason.value, "status": status},
            )
            if status == 401:
                STORE.set(_key("rejected", provider_id), "1", 24 * 3600)
                _cool_down(
                    provider_id,
                    UnavailableReason.PROVIDER_NOT_CONFIGURED,
                    COOLDOWN_SECONDS["rejected"],
                )
                raise
            if error.reason is UnavailableReason.RATE_LIMITED:
                wait = error.retry_after_seconds or COOLDOWN_SECONDS["rate_limited"]
                _cool_down(provider_id, UnavailableReason.RATE_LIMITED, wait)
                raise
            if status == 403 or error.reason is UnavailableReason.LICENSE_BLOCKED:
                # Outside the plan for this resource only: the query is remembered as refused
                # (see _cached), the provider keeps serving everything else.
                raise
            if not error.retryable or attempt == RETRY.max_attempts - 1:
                if error.retryable:
                    _cool_down(
                        provider_id, UnavailableReason.SOURCE_ERROR, COOLDOWN_SECONDS["source"]
                    )
                raise
            time.sleep(backoff_delay(attempt, RETRY))
            continue
        LOGGER.info("live_provider_ok", extra={"provider": provider_id})
        return payload
    raise NormalizationError(UnavailableReason.SOURCE_ERROR, f"{provider_id} sem resposta")


def _order(kind: str, capability: ProviderCapability, market: str, instrument: LiveInstrument):
    return tuple(
        provider_id
        for provider_id in PRECEDENCE.get((capability, market), ())
        if provider_id in _IMPLEMENTED[kind] and provider_id in instrument.symbols
    )


# --- Results ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class LiveResult:
    """One provider's validated value, or the reason nothing could be served."""

    value: Any | None
    provider: str | None
    fallback_used: bool
    freshness: Freshness
    fetched_at: datetime | None
    reason: UnavailableReason | None
    notes: tuple[str, ...] = ()
    primary: str | None = None


def _ref(instrument: LiveInstrument, provider_id: str) -> InstrumentRef:
    return InstrumentRef(
        instrument.canonical_id, instrument.symbols[provider_id], instrument.currency
    )


def _now() -> datetime:
    return datetime.now(UTC)


def _cached(
    key: str,
    kind: str,
    capability: ProviderCapability,
    instrument: LiveInstrument,
    fetch: Callable[[str], Any],
    encode: Callable[[Any], Any],
    decode: Callable[[Any], Any],
    fresh_seconds: Callable[[str], int],
) -> LiveResult:
    def read() -> dict[str, Any] | None:
        raw = STORE.get(key)
        return json.loads(raw) if raw else None

    def from_entry(entry: dict[str, Any], freshness: Freshness, reason=None) -> LiveResult:
        return LiveResult(
            decode(entry["value"]),
            entry["provider"],
            entry["fallback_used"],
            freshness,
            datetime.fromisoformat(entry["fetched_at"]),
            reason,
            tuple(entry.get("notes", ())),
            entry.get("primary"),
        )

    entry = read()
    if entry and _now() < datetime.fromisoformat(entry["fresh_until"]):
        return from_entry(entry, Freshness.FRESH)
    with _key_lock(key):
        entry = read()  # another request may have refreshed it meanwhile
        if entry and _now() < datetime.fromisoformat(entry["fresh_until"]):
            return from_entry(entry, Freshness.FRESH)
        order = _order(kind, capability, instrument.market, instrument)
        if not order:  # serve() would fall back to the whole precedence on an empty order
            return LiveResult(
                None,
                None,
                False,
                Freshness.UNAVAILABLE,
                None,
                UnavailableReason.DATASET_NOT_APPROVED,
            )
        refused = STORE.get(f"{key}:refused")
        if refused:  # this query was refused (plan or format): not asked again for a while
            reason = UnavailableReason(refused)
            if entry:
                return from_entry(entry, Freshness.STALE, reason)
            return LiveResult(None, None, False, Freshness.UNAVAILABLE, None, reason)
        breakers = {provider_id: _breaker(provider_id) for provider_id in order}
        result, trace = serve(
            capability,
            instrument.market,
            fetch,
            environ=os.environ,
            breakers=breakers,
            decide=_decide,
            order=order,
        )
        if result is not None and trace.served_by:
            value, notes = result
            fetched = _now()
            entry = {
                "value": encode(value),
                "provider": trace.served_by,
                "primary": trace.primary,
                "fallback_used": trace.fallback_used,
                "fetched_at": fetched.isoformat(),
                "fresh_until": (
                    fetched + timedelta(seconds=fresh_seconds(trace.served_by))
                ).isoformat(),
                "notes": list(notes),
            }
            STORE.set(key, json.dumps(entry), STALE_SECONDS)
            return from_entry(entry, Freshness.FRESH)
        reason = trace.reason or UnavailableReason.UNAVAILABLE
        if reason in REMEMBERED_REFUSALS:
            STORE.set(f"{key}:refused", reason.value, REFUSED_SECONDS)
        LOGGER.warning(
            "live_unavailable",
            extra={
                "canonical_id": instrument.canonical_id,
                "kind": kind,
                "attempts": [f"{a.provider_id}:{a.outcome}" for a in trace.attempts],
            },
        )
        if entry:
            return from_entry(entry, Freshness.STALE, reason)
        return LiveResult(None, None, False, Freshness.UNAVAILABLE, None, reason, (), trace.primary)


# --- Quotes ----------------------------------------------------------------------------------


def _accept(quote: CanonicalQuote) -> CanonicalQuote:
    if quote.quality_status is QualityStatus.QUARANTINED:
        raise NormalizationError(
            UnavailableReason.SCHEMA_UNSUPPORTED, "; ".join(quote.quality_notes) or "quarentena"
        )
    return quote


def _quote_from_bars(instrument: LiveInstrument, provider_id: str) -> CanonicalQuote:
    end = _now().date()
    series = _fetch_series(instrument, provider_id, start=end - timedelta(days=10))
    bars = series.bars
    if not bars:
        raise NormalizationError(UnavailableReason.UNAVAILABLE, "sem barra recente")
    last = bars[-1]
    previous = bars[-2].close if len(bars) >= 2 else None
    change = last.close - previous if previous else None
    return CanonicalQuote(
        canonical_id=instrument.canonical_id,
        provider=provider_id,
        dataset=DATASETS[(provider_id, "quote")],
        price=last.close,
        currency=last.currency,
        previous_close=previous,
        change=change,
        change_percent=(change / previous * Decimal("100"))
        if previous and change is not None
        else None,
        volume=last.volume,
        source_timestamp=last.timestamp,
        ingested_at=_now(),
        data_level=PLAN_LEVEL[provider_id],
        request_id="live",
    )


def _fetch_quote(instrument: LiveInstrument, provider_id: str) -> CanonicalQuote:
    ref = _ref(instrument, provider_id)
    common = {
        "dataset": DATASETS[(provider_id, "quote")],
        "request_id": "live",
        "now": _now(),
    }
    if provider_id == "brapi":
        payload = _send("brapi", vendors.brapi_quote_request(ref))
        return vendors.brapi_quote(payload, ref, data_level=PLAN_LEVEL["brapi"], **common)
    if provider_id == "twelve_data":
        payload = _send("twelve_data", vendors.twelve_data_quote_request(ref))
        return vendors.twelve_data_quote(
            payload, ref, data_level=PLAN_LEVEL["twelve_data"], **common
        )
    if provider_id == "alpha_vantage":
        payload = _send("alpha_vantage", vendors.alpha_vantage_quote_request(ref))
        return vendors.alpha_vantage_quote(payload, ref, **common)
    if provider_id == "massive":
        return _quote_from_bars(instrument, "massive")
    raise NormalizationError(
        UnavailableReason.SCHEMA_UNSUPPORTED, f"{provider_id} sem normalizador"
    )


def live_quote(canonical_id: str) -> LiveResult | None:
    """None when the instrument has no live source at all; otherwise a value or a reason."""

    instrument = LIVE_INSTRUMENTS.get(canonical_id)
    if instrument is None or instrument.market == "FX":
        return None

    def fetch(provider_id: str):
        quote = _accept(_fetch_quote(instrument, provider_id))
        return quote, tuple(quote.quality_notes)

    return _cached(
        _key("quote", canonical_id),
        "quote",
        ProviderCapability.LATEST_QUOTE,
        instrument,
        fetch,
        lambda quote: quote.model_dump(mode="json"),
        CanonicalQuote.model_validate,
        lambda provider_id: FRESH_SECONDS[provider_id],
    )


# --- Daily series ----------------------------------------------------------------------------


def _bar_json(bar: MarketBar) -> dict[str, Any]:
    return {
        "canonical_id": bar.canonical_id,
        "timestamp": bar.timestamp.isoformat(),
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
        "volume": None if bar.volume is None else str(bar.volume),
        "currency": bar.currency,
        "adjustment_type": bar.adjustment_type.value,
    }


def _fetch_series(
    instrument: LiveInstrument, provider_id: str, *, start: date | None = None
) -> SeriesResult:
    ref = _ref(instrument, provider_id)
    end = _now().date()
    if provider_id == "brapi":
        try:
            payload = _send("brapi", vendors.brapi_series_request(ref, "1y"))
        except NormalizationError as error:
            if error.http_status != 400:
                raise
            # The plan caps the window (documented: above the limit returns 400).
            payload = _send("brapi", vendors.brapi_series_request(ref, "3mo"))
        series = vendors.brapi_series(payload, ref)
    elif provider_id == "twelve_data":
        size = 15 if start else 800
        payload = _send("twelve_data", vendors.twelve_data_series_request(ref, size))
        series = vendors.twelve_data_series(payload, ref, adjustment=AdjustmentType.UNADJUSTED)
    elif provider_id == "massive":
        payload = _send(
            "massive", vendors.massive_bars_request(ref, start or end - timedelta(days=730), end)
        )
        series = vendors.massive_bars(payload, ref)
    else:
        raise NormalizationError(UnavailableReason.SCHEMA_UNSUPPORTED, f"{provider_id} sem série")
    quality = check_series(series.bars, now=_now(), expected_currency=instrument.currency)
    if quality.status is QualityStatus.QUARANTINED:
        raise NormalizationError(
            UnavailableReason.SCHEMA_UNSUPPORTED,
            "; ".join(f"{issue.code}: {issue.detail}" for issue in quality.issues),
        )
    if not series.bars:
        raise NormalizationError(UnavailableReason.UNAVAILABLE, "série vazia")
    return series


def live_series(canonical_id: str) -> LiveResult | None:
    """Unadjusted daily bars, cached as one window and cut per period by the caller."""

    instrument = LIVE_INSTRUMENTS.get(canonical_id)
    if instrument is None or instrument.market == "FX":
        return None

    def fetch(provider_id: str):
        series = _fetch_series(instrument, provider_id)
        return series.bars, series.notes

    return _cached(
        _key("series", canonical_id),
        "series",
        ProviderCapability.HISTORICAL_BARS,
        instrument,
        fetch,
        lambda bars: [_bar_json(bar) for bar in bars],
        lambda rows: tuple(MarketBar.from_payload(row) for row in rows),
        lambda _provider_id: SERIES_FRESH_SECONDS,
    )


# --- FX --------------------------------------------------------------------------------------


def live_fx(canonical_id: str) -> LiveResult | None:
    instrument = LIVE_INSTRUMENTS.get(canonical_id)
    if instrument is None or instrument.market != "FX":
        return None

    def fetch(provider_id: str):
        payload = _send(provider_id, vendors.open_exchange_rates_request())
        rate = vendors.open_exchange_rates_rate(
            payload,
            base=instrument.symbols[provider_id],
            quote=instrument.currency,
            dataset=DATASETS[(provider_id, "fx")],
            data_level=PLAN_LEVEL[provider_id],
            request_id="live",
            now=_now(),
        )
        return rate, ()

    return _cached(
        _key("fx", canonical_id),
        "fx",
        ProviderCapability.FX_RATES,
        instrument,
        fetch,
        lambda rate: rate.model_dump(mode="json"),
        CanonicalFxRate.model_validate,
        lambda provider_id: FRESH_SECONDS[provider_id],
    )


def limitations(provider_id: str | None, result: LiveResult) -> tuple[str, ...]:
    notes = [PRIVATE_USE_NOTE]
    if provider_id in METHODOLOGY:
        notes.append(METHODOLOGY[provider_id])
    if result.fallback_used and result.primary:
        notes.append(f"Fonte reserva: {result.primary} não respondeu e {provider_id} serviu.")
    if result.freshness is Freshness.STALE:
        notes.append("Último valor validado: a atualização falhou e o dado pode estar antigo.")
    notes.extend(result.notes)
    return tuple(notes)
