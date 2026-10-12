"""Request specs and normalizers per provider (ADR-025).

Only fields confirmed in each provider's official documentation on 2026-10-11 are read (see
`registry.REGISTRY[...].evidence`). Credentials never appear here: a `ProviderRequest` names
where the credential goes, and the transport injects it at send time.

`data_level` and `adjustment_type` come from the approved dataset, not from a guess in the
normalizer: the plan decides whether a feed is delayed or end of day.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from app.market_data.normalization import AdjustmentType, MarketBar
from app.providers.canonical import (
    CanonicalFxRate,
    CanonicalQuote,
    NormalizationError,
    QualityStatus,
    UnavailableReason,
)
from app.providers.models import DataLevel, ProviderError

UTC = timezone.utc


@dataclass(frozen=True)
class InstrumentRef:
    """Catalog identity plus the provider's own symbol for it."""

    canonical_id: str
    provider_symbol: str
    currency: str


@dataclass(frozen=True)
class ProviderRequest:
    provider_id: str
    method: str
    url: str
    params: Mapping[str, str] = field(default_factory=dict)
    # Where the transport puts the credential; the value itself is never stored here.
    auth_header: str | None = None
    auth_scheme: str | None = None
    auth_query_param: str | None = None


@dataclass(frozen=True)
class SeriesResult:
    bars: tuple[MarketBar, ...]
    partial: bool = False
    notes: tuple[str, ...] = ()


def _schema(message: str) -> NormalizationError:
    return NormalizationError(UnavailableReason.SCHEMA_UNSUPPORTED, message)


def _dec(value: Any, name: str, *, required: bool = True) -> Decimal | None:
    if value is None or value == "":
        if required:
            raise _schema(f"{name} ausente")
        return None
    if isinstance(value, (float, bool)):
        raise _schema(f"{name} chegou como float; o transporte deve ler JSON com Decimal")
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise _schema(f"{name} inválido") from exc
    if not number.is_finite():
        raise _schema(f"{name} inválido")
    return number


def _percent(value: Any, name: str) -> Decimal | None:
    if isinstance(value, str) and value.strip().endswith("%"):
        value = value.strip()[:-1]
    return _dec(value, name, required=False)


def _aware(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise _schema(f"{name} ausente")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _schema(f"{name} fora do formato ISO 8601") from exc
    if parsed.tzinfo is None:
        raise _schema(f"{name} sem fuso horário")
    return parsed.astimezone(UTC)


def _utc_datetime_or_session(value: Any, name: str) -> tuple[datetime | None, date | None]:
    """'YYYY-MM-DD' is a session date (no time); 'YYYY-MM-DD HH:MM:SS' is UTC by request."""

    if not isinstance(value, str) or not value:
        raise _schema(f"{name} ausente")
    try:
        if len(value) == 10:
            return None, date.fromisoformat(value)
        return datetime.fromisoformat(value).replace(tzinfo=UTC), None
    except ValueError as exc:
        raise _schema(f"{name} inválido") from exc


def _currency(value: Any, ref: InstrumentRef) -> tuple[str, tuple[str, ...]]:
    if not isinstance(value, str) or len(value) != 3 or value != value.upper():
        raise _schema("moeda ausente ou fora do padrão ISO")
    if value != ref.currency:
        return value, (f"CURRENCY_MISMATCH: fonte {value}, catálogo {ref.currency}",)
    return value, ()


# --- HTTP status per provider ------------------------------------------------------------

_STATUS_OVERRIDES: Mapping[tuple[str, int], UnavailableReason] = {
    # brapi: 403 = the plan does not include the requested data.
    ("brapi", 403): UnavailableReason.LICENSE_BLOCKED,
    # Open Exchange Rates: 429 `not_allowed` is a permission error, not a rate limit.
    ("open_exchange_rates", 429): UnavailableReason.LICENSE_BLOCKED,
    ("open_exchange_rates", 400): UnavailableReason.SCHEMA_UNSUPPORTED,
}


def reason_for_status(provider_id: str, status: int) -> UnavailableReason:
    if (provider_id, status) in _STATUS_OVERRIDES:
        return _STATUS_OVERRIDES[(provider_id, status)]
    if status in (401, 403):
        return UnavailableReason.PROVIDER_NOT_CONFIGURED
    if status == 429:
        return UnavailableReason.RATE_LIMITED
    return UnavailableReason.SOURCE_ERROR


_ERROR_CODES: Mapping[str, UnavailableReason] = {
    "PROVIDER_RATE_LIMIT": UnavailableReason.RATE_LIMITED,
    "PROVIDER_UNAUTHORIZED": UnavailableReason.PROVIDER_NOT_CONFIGURED,
    "PROVIDER_NOT_CONFIGURED": UnavailableReason.PROVIDER_NOT_CONFIGURED,
    "PROVIDER_PAYLOAD_INVALID": UnavailableReason.SCHEMA_UNSUPPORTED,
    "NORMALIZATION_REQUIRED": UnavailableReason.SCHEMA_UNSUPPORTED,
}


def reason_for_error(error: Exception) -> UnavailableReason:
    """Public reason for any provider failure; unknown failures are SOURCE_ERROR."""

    if isinstance(error, NormalizationError):
        return error.reason
    if isinstance(error, PermissionError):
        return UnavailableReason.LICENSE_BLOCKED
    if isinstance(error, ProviderError):
        return _ERROR_CODES.get(error.code, UnavailableReason.SOURCE_ERROR)
    return UnavailableReason.SOURCE_ERROR


# --- brapi ---------------------------------------------------------------------------------


def brapi_quote_request(ref: InstrumentRef) -> ProviderRequest:
    return ProviderRequest(
        "brapi",
        "GET",
        "https://brapi.dev/api/v2/stocks/quote",
        {"symbols": ref.provider_symbol},
        auth_header="Authorization",
        auth_scheme="Bearer",
    )


def brapi_quote(
    payload: Mapping[str, Any],
    ref: InstrumentRef,
    *,
    dataset: str,
    data_level: DataLevel,
    request_id: str,
    now: datetime,
) -> CanonicalQuote:
    results = payload.get("results")
    if not isinstance(results, list):
        raise _schema("results ausente")
    item = next(
        (
            row
            for row in results
            if isinstance(row, dict) and row.get("requestedSymbol") == ref.provider_symbol
        ),
        None,
    )
    if item is None or not isinstance(item.get("data"), dict):
        raise _schema(f"sem resultado para {ref.provider_symbol}")
    data = item["data"]
    notes: list[str] = []
    if item.get("changed") is True:
        notes.append(f"TICKER_RENAMED: {ref.provider_symbol} -> {item.get('symbol')}")
    currency, mismatch = _currency(data.get("currency"), ref)
    notes.extend(mismatch)
    return CanonicalQuote(
        canonical_id=ref.canonical_id,
        provider="brapi",
        dataset=dataset,
        price=_dec(data.get("regularMarketPrice"), "regularMarketPrice"),
        currency=currency,
        change=_dec(data.get("regularMarketChange"), "regularMarketChange", required=False),
        change_percent=_dec(
            data.get("regularMarketChangePercent"), "regularMarketChangePercent", required=False
        ),
        volume=_dec(data.get("regularMarketVolume"), "regularMarketVolume", required=False),
        source_timestamp=_aware(data.get("regularMarketTime"), "regularMarketTime"),
        ingested_at=now,
        data_level=data_level,
        quality_status=QualityStatus.QUARANTINED if notes else QualityStatus.VALID,
        quality_notes=tuple(notes),
        request_id=request_id,
    )


def brapi_series_request(ref: InstrumentRef, range_: str) -> ProviderRequest:
    # brapi OpenAPI 3.0.0 (read 2026-10-12): daily open/high/low/close "podem vir ajustados";
    # only includeRaw (Pro plan) returns rawOpen/rawHigh/rawLow/rawClose without adjustment.
    return ProviderRequest(
        "brapi",
        "GET",
        "https://brapi.dev/api/v2/stocks/historical",
        {
            "symbols": ref.provider_symbol,
            "range": range_,
            "interval": "1d",
            "sortOrder": "asc",
            "includeRaw": "true",
        },
        auth_header="Authorization",
        auth_scheme="Bearer",
    )


_BRAPI_RAW = {"open": "rawOpen", "high": "rawHigh", "low": "rawLow", "close": "rawClose"}


def brapi_series(payload: Mapping[str, Any], ref: InstrumentRef) -> SeriesResult:
    """Unadjusted daily bars from the raw* fields; a session without them is left out."""

    results = payload.get("results")
    if not isinstance(results, list):
        raise _schema("results ausente")
    item = next(
        (
            row
            for row in results
            if isinstance(row, dict) and row.get("requestedSymbol") == ref.provider_symbol
        ),
        None,
    )
    data = item.get("data") if isinstance(item, dict) else None
    rows = data.get("historicalDataPrice") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise _schema(f"historicalDataPrice ausente para {ref.provider_symbol}")
    raw_rows = [
        {"date": row.get("date"), "volume": row.get("volume")}
        | {key: row.get(source) for key, source in _BRAPI_RAW.items()}
        for row in rows
        if isinstance(row, dict)
        and all(row.get(source) is not None for source in _BRAPI_RAW.values())
    ]
    if rows and not raw_rows:
        raise _schema("sem preço sem ajuste (raw*): includeRaw exige o plano Pro da brapi")

    def instant(row: Mapping[str, Any]) -> datetime:
        stamp = row.get("date")
        if not isinstance(stamp, int) or isinstance(stamp, bool):
            raise _schema("date ausente ou não inteiro")
        # Documented as the session date in Unix seconds.
        return datetime.fromtimestamp(stamp, UTC)

    fields = {key: key for key in ("open", "high", "low", "close", "volume")}
    skipped = len(rows) - len(raw_rows)
    return SeriesResult(
        _bars(raw_rows, ref, ref.currency, AdjustmentType.UNADJUSTED, instant, fields),
        partial=skipped > 0,
        notes=(f"RAW_MISSING: {skipped} pregões sem preço sem ajuste",) if skipped else (),
    )


# --- Twelve Data ---------------------------------------------------------------------------


def _twelve_data_error(payload: Mapping[str, Any]) -> None:
    if payload.get("status") == "error":
        code = payload.get("code")
        status = code if isinstance(code, int) else 0
        raise NormalizationError(
            reason_for_status("twelve_data", status),
            f"Twelve Data respondeu erro {status}",
            retryable=status == 429,
            http_status=status or None,
        )


def twelve_data_quote_request(ref: InstrumentRef) -> ProviderRequest:
    return ProviderRequest(
        "twelve_data",
        "GET",
        "https://api.twelvedata.com/quote",
        {"symbol": ref.provider_symbol, "timezone": "UTC"},
        auth_header="Authorization",
        auth_scheme="apikey",
    )


def twelve_data_quote(
    payload: Mapping[str, Any],
    ref: InstrumentRef,
    *,
    dataset: str,
    data_level: DataLevel,
    request_id: str,
    now: datetime,
) -> CanonicalQuote:
    _twelve_data_error(payload)
    if payload.get("symbol") != ref.provider_symbol:
        raise _schema("símbolo da resposta difere do pedido")
    currency, notes = _currency(payload.get("currency"), ref)
    timestamp, session = _utc_datetime_or_session(payload.get("datetime"), "datetime")
    return CanonicalQuote(
        canonical_id=ref.canonical_id,
        provider="twelve_data",
        dataset=dataset,
        price=_dec(payload.get("close"), "close"),
        currency=currency,
        previous_close=_dec(payload.get("previous_close"), "previous_close", required=False),
        change=_dec(payload.get("change"), "change", required=False),
        change_percent=_percent(payload.get("percent_change"), "percent_change"),
        volume=_dec(payload.get("volume"), "volume", required=False),
        source_timestamp=timestamp,
        session_date=session,
        ingested_at=now,
        data_level=data_level,
        quality_status=QualityStatus.QUARANTINED if notes else QualityStatus.VALID,
        quality_notes=notes,
        request_id=request_id,
    )


def twelve_data_series_request(ref: InstrumentRef, outputsize: int = 30) -> ProviderRequest:
    # `adjust` defaults to "splits" (docs read 2026-10-12); "none" keeps the series unadjusted.
    return ProviderRequest(
        "twelve_data",
        "GET",
        "https://api.twelvedata.com/time_series",
        {
            "symbol": ref.provider_symbol,
            "interval": "1day",
            "outputsize": str(outputsize),
            "timezone": "UTC",
            "adjust": "none",
        },
        auth_header="Authorization",
        auth_scheme="apikey",
    )


def _bars(
    rows: Sequence[Mapping[str, Any]],
    ref: InstrumentRef,
    currency: str,
    adjustment: AdjustmentType,
    timestamp_of: Any,
    fields: Mapping[str, str],
) -> tuple[MarketBar, ...]:
    bars = []
    for row in rows:
        try:
            bars.append(
                MarketBar.from_payload(
                    {
                        "canonical_id": ref.canonical_id,
                        "currency": currency,
                        "adjustment_type": adjustment.value,
                        "timestamp": timestamp_of(row).isoformat(),
                        **{key: row.get(source) for key, source in fields.items()},
                    }
                )
            )
        except ValueError as exc:
            raise _schema(f"barra inválida: {exc}") from exc
    return tuple(sorted(bars, key=lambda bar: bar.timestamp))


_TWELVE_DATA_FIELDS = {key: key for key in ("open", "high", "low", "close", "volume")}
_MASSIVE_FIELDS = {"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"}


def twelve_data_series(
    payload: Mapping[str, Any], ref: InstrumentRef, *, adjustment: AdjustmentType
) -> SeriesResult:
    _twelve_data_error(payload)
    meta, values = payload.get("meta"), payload.get("values")
    if not isinstance(meta, dict) or not isinstance(values, list):
        raise _schema("meta ou values ausente")
    currency, notes = _currency(meta.get("currency"), ref)
    if notes:
        raise _schema(notes[0])

    def instant(row: Mapping[str, Any]) -> datetime:
        moment, session = _utc_datetime_or_session(row.get("datetime"), "datetime")
        return moment or datetime(session.year, session.month, session.day, tzinfo=UTC)

    return SeriesResult(_bars(values, ref, currency, adjustment, instant, _TWELVE_DATA_FIELDS))


# --- Alpha Vantage -------------------------------------------------------------------------


def alpha_vantage_quote_request(ref: InstrumentRef) -> ProviderRequest:
    return ProviderRequest(
        "alpha_vantage",
        "GET",
        "https://www.alphavantage.co/query",
        {"function": "GLOBAL_QUOTE", "symbol": ref.provider_symbol},
        auth_query_param="apikey",
    )


def alpha_vantage_quote(
    payload: Mapping[str, Any],
    ref: InstrumentRef,
    *,
    dataset: str,
    request_id: str,
    now: datetime,
) -> CanonicalQuote:
    quote = payload.get("Global Quote")
    if not isinstance(quote, dict) or not quote:
        # The documentation read does not define the body of a limit or error response.
        raise _schema("resposta sem 'Global Quote' (formato de erro não documentado)")
    if quote.get("01. symbol") != ref.provider_symbol:
        raise _schema("símbolo da resposta difere do pedido")
    session = quote.get("07. latest trading day")
    try:
        session_date = date.fromisoformat(session) if isinstance(session, str) else None
    except ValueError:
        session_date = None
    if session_date is None:
        raise _schema("07. latest trading day ausente ou inválido")
    return CanonicalQuote(
        canonical_id=ref.canonical_id,
        provider="alpha_vantage",
        dataset=dataset,
        price=_dec(quote.get("05. price"), "05. price"),
        # GLOBAL_QUOTE carries no currency: it comes from the catalog and says so.
        currency=ref.currency,
        previous_close=_dec(quote.get("08. previous close"), "08. previous close", required=False),
        change=_dec(quote.get("09. change"), "09. change", required=False),
        change_percent=_percent(quote.get("10. change percent"), "10. change percent"),
        volume=_dec(quote.get("06. volume"), "06. volume", required=False),
        session_date=session_date,
        ingested_at=now,
        # Documented: GLOBAL_QUOTE updates at the end of each trading day by default.
        data_level=DataLevel.EOD,
        quality_notes=("CURRENCY_FROM_CATALOG",),
        request_id=request_id,
    )


# --- Open Exchange Rates -------------------------------------------------------------------


def open_exchange_rates_request() -> ProviderRequest:
    return ProviderRequest(
        "open_exchange_rates",
        "GET",
        "https://openexchangerates.org/api/latest.json",
        auth_query_param="app_id",
    )


def open_exchange_rates_rate(
    payload: Mapping[str, Any],
    *,
    base: str,
    quote: str,
    dataset: str,
    data_level: DataLevel,
    request_id: str,
    now: datetime,
) -> CanonicalFxRate:
    if payload.get("error") is True:
        status = payload.get("status")
        status = status if isinstance(status, int) else 0
        raise NormalizationError(
            reason_for_status("open_exchange_rates", status),
            f"Open Exchange Rates respondeu {payload.get('message', 'erro')}",
            http_status=status or None,
        )
    if payload.get("base") != base:
        raise _schema(f"base {payload.get('base')} difere da pedida {base}")
    rates = payload.get("rates")
    if not isinstance(rates, dict) or quote not in rates:
        raise _schema(f"taxa {quote} ausente")
    timestamp = payload.get("timestamp")
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        raise _schema("timestamp ausente ou não inteiro")
    return CanonicalFxRate(
        base_currency=base,
        quote_currency=quote,
        rate=_dec(rates[quote], f"rates.{quote}"),
        provider="open_exchange_rates",
        dataset=dataset,
        source_timestamp=datetime.fromtimestamp(timestamp, UTC),
        ingested_at=now,
        data_level=data_level,
        request_id=request_id,
    )


# --- Massive -------------------------------------------------------------------------------


def massive_bars_request(ref: InstrumentRef, start: date, end: date) -> ProviderRequest:
    return ProviderRequest(
        "massive",
        "GET",
        f"https://api.massive.com/v2/aggs/ticker/{ref.provider_symbol}/range/1/day/"
        f"{start.isoformat()}/{end.isoformat()}",
        # Unadjusted on purpose: the default (adjusted=true) would mix with unadjusted series.
        {"adjusted": "false", "sort": "asc", "limit": "5000"},
        auth_header="Authorization",
        auth_scheme="Bearer",
    )


def massive_bars(payload: Mapping[str, Any], ref: InstrumentRef) -> SeriesResult:
    if payload.get("adjusted") is not False:
        raise _schema("série ajustada ou sem o campo adjusted; pedido foi adjusted=false")
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise _schema("results inválido")

    def instant(row: Mapping[str, Any]) -> datetime:
        stamp = row.get("t")
        if not isinstance(stamp, int) or isinstance(stamp, bool):
            raise _schema("t ausente ou não inteiro")
        # Documented as a Unix millisecond timestamp (start of the window).
        return datetime.fromtimestamp(stamp / 1000, UTC)

    bars = _bars(results, ref, ref.currency, AdjustmentType.UNADJUSTED, instant, _MASSIVE_FIELDS)
    partial = bool(payload.get("next_url"))
    return SeriesResult(
        bars,
        partial=partial,
        notes=("PAGINATED: next_url presente; série incompleta",) if partial else (),
    )
