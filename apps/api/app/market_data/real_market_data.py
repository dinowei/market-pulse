"""Public contracts built from live provider data (ADR-027).

The same PublicQuote, PublicHistorySeries and BenchmarkItem the rest of the API returns, now
filled from `live_data`. Nothing is DEMO here: when no provider can serve, the answer is
UNAVAILABLE with its reason, never a synthetic value. Anonymous visitors of the private
staging get SESSION_REQUIRED, because the owner's approval covers only the owner's session.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal

from app.contracts import (
    BenchmarkItem,
    HistoryPeriod,
    PublicHistoryPoint,
    PublicHistorySeries,
    PublicQuote,
    SeriesMode,
)
from app.instruments.catalog import InstrumentCatalogEntry, get_catalog
from app.market_data import live_data
from app.market_data.benchmarks import benchmark_definitions
from app.market_data.live_data import LIVE_INSTRUMENTS, LiveResult
from app.market_data.normalization import MarketBar
from app.portfolios.performance import FxMark, PriceMark
from app.providers.canonical import CanonicalFxRate, CanonicalQuote, UnavailableReason
from app.providers.models import DataLevel, Freshness
from app.providers.registry import OWNER_PRIVATE_LICENSE

NO_PROVIDER = "Nenhum provider aprovado pelo responsável cobre este dado."
SESSION_NOTE = (
    "Dados reais só aparecem na sessão do responsável: a licença aprovada cobre uso privado."
)
NOT_CONFIGURED_NOTE = (
    "Nenhum provider de dados reais está configurado neste ambiente; DEMO não é usado aqui."
)
UNITS = {
    "index.br.b3.ibovespa": "Valor em pontos do índice.",
    "fx.global.usd-brl": "Valor em reais por 1 dólar americano.",
}
_SESSION_COUNT = {HistoryPeriod.ONE_D: 1, HistoryPeriod.FIVE_D: 5}


def _catalog_entry(canonical_id: str) -> InstrumentCatalogEntry | None:
    return next((entry for entry in get_catalog() if entry.canonical_id == canonical_id), None)


def _nominal_level(canonical_id: str, primary: str | None = None) -> DataLevel:
    """The level the configured dataset delivers; used to label an unavailable answer."""

    instrument = LIVE_INSTRUMENTS.get(canonical_id)
    provider = primary or (next(iter(instrument.symbols)) if instrument else None)
    return live_data.PLAN_LEVEL.get(provider, DataLevel.EOD)


def _latency_ms(official: datetime | None, collected: datetime) -> int | None:
    if official is None:
        return None
    return max(0, int((collected - official).total_seconds() * 1000))


def _timezone(canonical_id: str) -> str | None:
    instrument = LIVE_INSTRUMENTS.get(canonical_id)
    return instrument.timezone if instrument else None


# --- Quotes ----------------------------------------------------------------------------------


def unavailable_quote(
    entry: InstrumentCatalogEntry,
    request_id: str,
    reason: UnavailableReason,
    note: str,
    *,
    primary: str | None = None,
) -> PublicQuote:
    now = datetime.now(UTC)
    return PublicQuote(
        canonical_id=entry.canonical_id,
        symbol=entry.symbol,
        name=entry.name,
        asset_type=entry.instrument_type,
        exchange=entry.exchange,
        currency=entry.currency,
        data_level=_nominal_level(entry.canonical_id, primary),
        freshness=Freshness.UNAVAILABLE,
        provider=primary or "none",
        dataset="none",
        timestamp_collected=now,
        observed_at=now,
        timezone=_timezone(entry.canonical_id),
        is_demo=False,
        limitations=(note,),
        unavailable_reason=reason.value,
        request_id=request_id,
    )


def real_quote(canonical_id: str, request_id: str) -> PublicQuote:
    entry = _catalog_entry(canonical_id)
    if entry is None:
        raise KeyError(canonical_id)
    result = live_data.live_quote(canonical_id)
    if result is None:
        return unavailable_quote(
            entry, request_id, UnavailableReason.DATASET_NOT_APPROVED, NO_PROVIDER
        )
    if result.value is None:
        reason = result.reason or UnavailableReason.UNAVAILABLE
        note = live_data.PRIVATE_USE_NOTE
        return unavailable_quote(entry, request_id, reason, note, primary=result.primary)
    quote: CanonicalQuote = result.value
    now = datetime.now(UTC)
    return PublicQuote(
        canonical_id=canonical_id,
        symbol=entry.symbol,
        name=entry.name,
        asset_type=entry.instrument_type,
        exchange=entry.exchange,
        currency=quote.currency,
        price=quote.price,
        change=quote.change,
        change_percent=quote.change_percent,
        data_level=quote.data_level,
        freshness=result.freshness,
        provider=quote.provider,
        dataset=quote.dataset,
        timestamp_official=quote.source_timestamp,
        timestamp_collected=quote.ingested_at,
        latency_ms=_latency_ms(quote.source_timestamp, quote.ingested_at),
        session_date=quote.session_date,
        timezone=_timezone(canonical_id),
        observed_at=now,
        quality_status=quote.quality_status.value,
        license_status=OWNER_PRIVATE_LICENSE,
        is_demo=False,
        fallback_used=result.fallback_used,
        limitations=live_data.limitations(quote.provider, result),
        unavailable_reason=result.reason.value if result.reason else None,
        request_id=request_id,
    )


def session_required_quote(canonical_id: str, request_id: str) -> PublicQuote:
    entry = _catalog_entry(canonical_id)
    if entry is None:
        raise KeyError(canonical_id)
    return unavailable_quote(entry, request_id, UnavailableReason.SESSION_REQUIRED, SESSION_NOTE)


def not_configured_quote(canonical_id: str, request_id: str) -> PublicQuote:
    entry = _catalog_entry(canonical_id)
    if entry is None:
        raise KeyError(canonical_id)
    return unavailable_quote(
        entry, request_id, UnavailableReason.PROVIDER_NOT_CONFIGURED, NOT_CONFIGURED_NOTE
    )


# --- Series ----------------------------------------------------------------------------------


def _identity(canonical_id: str) -> tuple[str, str] | None:
    entry = _catalog_entry(canonical_id)
    if entry is not None:
        return entry.symbol, entry.currency
    definition = benchmark_definitions().get(canonical_id)
    return (definition.symbol, definition.currency) if definition else None


def unavailable_series(
    canonical_id: str,
    period: HistoryPeriod,
    mode: SeriesMode,
    request_id: str,
    reason: UnavailableReason,
    note: str,
    *,
    primary: str | None = None,
) -> PublicHistorySeries:
    identity = _identity(canonical_id)
    if identity is None:
        raise KeyError(canonical_id)
    symbol, currency = identity
    now = datetime.now(UTC)
    return PublicHistorySeries(
        canonical_id=canonical_id,
        symbol=symbol,
        period=period,
        mode=mode,
        adjustment_type="UNADJUSTED",
        currency=currency,
        data_level=DataLevel.EOD,
        freshness=Freshness.UNAVAILABLE,
        provider=primary or "none",
        dataset="none",
        timestamp_collected=now,
        observed_at=now,
        timezone=_timezone(canonical_id),
        is_demo=False,
        limitations=(note,),
        points=[],
        tabular_fallback=True,
        accessibility={"reduced_motion": True, "smoothed": False},
        unavailable_reason=reason.value,
        request_id=request_id,
    )


def _window(bars: tuple[MarketBar, ...], period: HistoryPeriod) -> tuple[MarketBar, ...]:
    if period in _SESSION_COUNT:
        return bars[-_SESSION_COUNT[period] :]
    from app.market_data.public_market_data import _period_window

    start, end = _period_window(period)
    return tuple(bar for bar in bars if start.date() <= bar.timestamp.date() <= end.date())


def real_series(
    canonical_id: str,
    period: HistoryPeriod,
    mode: SeriesMode,
    request_id: str,
    adjustment_type: str = "UNADJUSTED",
) -> PublicHistorySeries:
    if _identity(canonical_id) is None:
        raise KeyError(canonical_id)
    if adjustment_type != "UNADJUSTED":
        return unavailable_series(
            canonical_id,
            period,
            mode,
            request_id,
            UnavailableReason.DATASET_NOT_APPROVED,
            "As fontes aprovadas entregam só a série sem ajuste.",
        )
    result = live_data.live_series(canonical_id)
    if result is None:
        return unavailable_series(
            canonical_id,
            period,
            mode,
            request_id,
            UnavailableReason.DATASET_NOT_APPROVED,
            NO_PROVIDER,
        )
    if result.value is None:
        return unavailable_series(
            canonical_id,
            period,
            mode,
            request_id,
            result.reason or UnavailableReason.UNAVAILABLE,
            live_data.PRIVATE_USE_NOTE,
            primary=result.primary,
        )
    bars = _window(result.value, period)
    if not bars:
        return unavailable_series(
            canonical_id,
            period,
            mode,
            request_id,
            UnavailableReason.UNAVAILABLE,
            "A fonte não tem pregões neste período.",
            primary=result.provider,
        )
    base = bars[0].close
    points = [
        PublicHistoryPoint(
            timestamp=bar.timestamp,
            session_date=bar.timestamp.date(),
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            value=bar.close,
            index_100=bar.close / base * Decimal("100"),
        )
        for bar in bars
    ]
    last = bars[-1]
    # Twelve Data names only the session of a daily bar: its time is not a source timestamp.
    session_only = result.provider == "twelve_data"
    official = None if session_only else last.timestamp
    collected = result.fetched_at or datetime.now(UTC)
    notes = live_data.limitations(result.provider, result)
    if period in _SESSION_COUNT:
        notes = (*notes, f"Série diária: {period.value} mostra os últimos pregões.")
    return PublicHistorySeries(
        canonical_id=canonical_id,
        symbol=_identity(canonical_id)[0],
        period=period,
        mode=mode,
        adjustment_type="UNADJUSTED",
        currency=last.currency,
        data_level=DataLevel.EOD,
        freshness=result.freshness,
        provider=result.provider,
        dataset=live_data.DATASETS[(result.provider, "series")],
        timestamp_official=official,
        timestamp_collected=collected,
        latency_ms=_latency_ms(official, collected),
        session_date=last.timestamp.date() if session_only else None,
        timezone=_timezone(canonical_id),
        observed_at=datetime.now(UTC),
        quality_status="VALID",
        license_status=OWNER_PRIVATE_LICENSE,
        is_demo=False,
        fallback_used=result.fallback_used,
        limitations=notes,
        points=points,
        tabular_fallback=True,
        accessibility={"reduced_motion": True, "smoothed": False},
        unavailable_reason=result.reason.value if result.reason else None,
        request_id=request_id,
    )


def session_required_series(
    canonical_id: str, period: HistoryPeriod, mode: SeriesMode, request_id: str
) -> PublicHistorySeries:
    return unavailable_series(
        canonical_id, period, mode, request_id, UnavailableReason.SESSION_REQUIRED, SESSION_NOTE
    )


def not_configured_series(
    canonical_id: str, period: HistoryPeriod, mode: SeriesMode, request_id: str
) -> PublicHistorySeries:
    return unavailable_series(
        canonical_id,
        period,
        mode,
        request_id,
        UnavailableReason.PROVIDER_NOT_CONFIGURED,
        NOT_CONFIGURED_NOTE,
    )


# --- Benchmarks ------------------------------------------------------------------------------


def _benchmark_unavailable(
    canonical_id: str, reason: UnavailableReason, note: str
) -> BenchmarkItem:
    definition = benchmark_definitions()[canonical_id]
    now = datetime.now(UTC)
    return BenchmarkItem(
        canonical_id=canonical_id,
        symbol=definition.symbol,
        name=definition.name,
        currency=definition.currency,
        data_level=_nominal_level(canonical_id),
        freshness=Freshness.UNAVAILABLE,
        source="none",
        dataset="none",
        timestamp_collected=now,
        observed_at=now,
        timezone=_timezone(canonical_id),
        is_demo=False,
        limitations=(note,),
        unavailable_reason=reason.value,
    )


def _benchmark_from(canonical_id: str, result: LiveResult) -> BenchmarkItem:
    definition = benchmark_definitions()[canonical_id]
    value = result.value
    if isinstance(value, CanonicalFxRate):
        amount, change, official, collected = (
            value.rate,
            None,
            value.source_timestamp,
            value.ingested_at,
        )
        provider, dataset, level = value.provider, value.dataset, value.data_level
    else:
        quote: CanonicalQuote = value
        amount, change, official, collected = (
            quote.price,
            quote.change_percent,
            quote.source_timestamp,
            quote.ingested_at,
        )
        provider, dataset, level = quote.provider, quote.dataset, quote.data_level
    notes = live_data.limitations(provider, result)
    if canonical_id in UNITS:
        notes = (*notes, UNITS[canonical_id])
    return BenchmarkItem(
        canonical_id=canonical_id,
        symbol=definition.symbol,
        name=definition.name,
        currency=definition.currency,
        value=amount,
        change_percent=change,
        data_level=level,
        freshness=result.freshness,
        source=provider,
        dataset=dataset,
        timestamp_official=official,
        timestamp_collected=collected,
        observed_at=datetime.now(UTC),
        timezone=_timezone(canonical_id),
        quality_status="VALID",
        license_status=OWNER_PRIVATE_LICENSE,
        is_demo=False,
        fallback_used=result.fallback_used,
        limitations=notes,
        unavailable_reason=result.reason.value if result.reason else None,
    )


def real_benchmarks() -> list[BenchmarkItem]:
    items = []
    for canonical_id in benchmark_definitions():
        result = live_data.live_fx(canonical_id) or live_data.live_quote(canonical_id)
        if result is None:
            items.append(
                _benchmark_unavailable(
                    canonical_id, UnavailableReason.DATASET_NOT_APPROVED, NO_PROVIDER
                )
            )
        elif result.value is None:
            reason = result.reason or UnavailableReason.UNAVAILABLE
            items.append(_benchmark_unavailable(canonical_id, reason, live_data.PRIVATE_USE_NOTE))
        else:
            items.append(_benchmark_from(canonical_id, result))
    return items


def session_required_benchmarks() -> list[BenchmarkItem]:
    return [
        _benchmark_unavailable(canonical_id, UnavailableReason.SESSION_REQUIRED, SESSION_NOTE)
        for canonical_id in benchmark_definitions()
    ]


def not_configured_benchmarks() -> list[BenchmarkItem]:
    return [
        _benchmark_unavailable(
            canonical_id, UnavailableReason.PROVIDER_NOT_CONFIGURED, NOT_CONFIGURED_NOTE
        )
        for canonical_id in benchmark_definitions()
    ]


# --- Portfolio marks -------------------------------------------------------------------------


def _session_instant(quote: CanonicalQuote) -> tuple[datetime, tuple[str, ...]]:
    if quote.source_timestamp is not None:
        return quote.source_timestamp, ()
    # Session-only source: the date is the trading day; 00:00 UTC marks the date, not a time.
    return datetime.combine(quote.session_date, time.min, UTC), (
        "A fonte informa só a data do pregão; o horário mostrado marca a data, não a cotação.",
    )


def real_price_marks(canonical_ids: list[str | None]) -> tuple[dict[str, PriceMark], dict]:
    """Current marks from live quotes; an instrument without one stays missing, never 42.42."""

    prices: dict[str, PriceMark] = {}
    for canonical_id in dict.fromkeys(item for item in canonical_ids if item):
        result = live_data.live_quote(canonical_id)
        if result is None or result.value is None:
            continue
        quote: CanonicalQuote = result.value
        instant, notes = _session_instant(quote)
        prices[canonical_id] = PriceMark(
            canonical_id,
            quote.price,
            quote.currency,
            quote.provider,
            quote.dataset,
            quote.data_level,
            result.freshness,
            instant,
            quote.ingested_at,
            (*live_data.limitations(quote.provider, result), *notes),
        )
    fx: dict[tuple[str, str], FxMark] = {}
    rate_result = live_data.live_fx("fx.global.usd-brl")
    if rate_result is not None and rate_result.value is not None:
        rate: CanonicalFxRate = rate_result.value
        fx[("USD", "BRL")] = FxMark(
            "USD",
            "BRL",
            rate.rate,
            rate.provider,
            rate.dataset,
            rate.data_level,
            rate_result.freshness,
            rate.source_timestamp,
            rate.ingested_at,
            live_data.limitations(rate.provider, rate_result),
        )
    return prices, fx


def real_price_marks_on(canonical_ids: list[str | None], day: date) -> dict[str, PriceMark]:
    """Marks for a past day: that session's close from the daily series, or nothing."""

    prices: dict[str, PriceMark] = {}
    for canonical_id in dict.fromkeys(item for item in canonical_ids if item):
        result = live_data.live_series(canonical_id)
        if result is None or result.value is None:
            continue
        bar = next((item for item in reversed(result.value) if item.timestamp.date() <= day), None)
        if bar is None:
            continue
        prices[canonical_id] = PriceMark(
            canonical_id,
            bar.close,
            bar.currency,
            result.provider,
            live_data.DATASETS[(result.provider, "series")],
            DataLevel.EOD,
            result.freshness,
            bar.timestamp,
            result.fetched_at or datetime.now(UTC),
            live_data.limitations(result.provider, result),
        )
    return prices
