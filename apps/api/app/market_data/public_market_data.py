"""Safe public read models backed only by local synthetic fixtures."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.contracts import (
    HistoryPeriod,
    PublicHistoryPoint,
    PublicHistorySeries,
    PublicQuote,
    SeriesMode,
)
from app.core.config import get_settings
from app.instruments.catalog import (
    CatalogStatus,
    CoverageTier,
    DataSupportStatus,
    InstrumentCatalogEntry,
    get_catalog,
)
from app.providers.demo import DemoProvider
from app.providers.models import DataLevel, Freshness

UTC = timezone.utc
_DEMO = DemoProvider()


def _find(canonical_id: str) -> InstrumentCatalogEntry | None:
    return next((entry for entry in get_catalog() if entry.canonical_id == canonical_id), None)


def _unavailable_quote(
    entry: InstrumentCatalogEntry | None, canonical_id: str, request_id: str
) -> PublicQuote:
    return PublicQuote(
        canonical_id=canonical_id,
        symbol=entry.symbol if entry else canonical_id,
        name=entry.name if entry else canonical_id,
        asset_type=entry.instrument_type if entry else "UNKNOWN",
        exchange=entry.exchange if entry else None,
        currency=entry.currency if entry else "XXX",
        data_level=DataLevel.DEMO,
        freshness=Freshness.UNAVAILABLE,
        provider="none",
        dataset="none",
        timestamp_collected=datetime.now(UTC),
        limitations=("Nenhum dataset aprovado está disponível para este instrumento.",),
        unavailable_reason="DATASET_NOT_APPROVED",
        request_id=request_id,
    )


def public_quote(canonical_id: str, request_id: str) -> PublicQuote:
    entry = _find(canonical_id)
    if entry is None:
        raise KeyError(canonical_id)
    if get_settings().demo_enabled:
        from app.demo.dataset import DEMO_LIMITATIONS
        from app.demo.read_models import bar_rows, quote_row

        row = quote_row(canonical_id)
        if row is None:
            return _unavailable_quote(entry, canonical_id, request_id)
        bars = bar_rows(canonical_id)
        previous = bars[-2]["close"] if len(bars) >= 2 else None
        change = row["price"] - previous if previous else None
        return PublicQuote(
            canonical_id=canonical_id,
            symbol=entry.symbol,
            name=entry.name,
            asset_type=entry.instrument_type,
            exchange=entry.exchange,
            currency=row["currency"],
            price=row["price"],
            change=change,
            change_percent=change / previous * Decimal("100") if previous else None,
            data_level=row["data_level"],
            freshness=row["freshness"],
            provider=row["provider"],
            dataset=row["dataset"],
            timestamp_official=row["source_timestamp"],
            timestamp_collected=row["collected_at"],
            latency_ms=max(
                0, int((row["collected_at"] - row["source_timestamp"]).total_seconds() * 1000)
            ),
            limitations=DEMO_LIMITATIONS,
            request_id=request_id,
        )
    if entry.coverage_tier is not CoverageTier.P0_OPERATIONAL or (
        entry.catalog_status is CatalogStatus.OUT_OF_SCOPE
        or entry.data_support_status is DataSupportStatus.UNAVAILABLE
    ):
        return _unavailable_quote(entry, canonical_id, request_id)
    result = _DEMO.latest_quote(canonical_id)
    provenance = result.provenance
    return PublicQuote(
        canonical_id=canonical_id,
        symbol=entry.symbol,
        name=entry.name,
        asset_type=entry.instrument_type,
        exchange=entry.exchange,
        currency=entry.currency,
        price=result.value,
        change=Decimal("0"),
        change_percent=Decimal("0"),
        data_level=provenance.data_level,
        freshness=provenance.freshness,
        provider=provenance.provider,
        dataset=provenance.dataset,
        timestamp_official=provenance.source_timestamp,
        timestamp_collected=provenance.collected_at,
        latency_ms=max(
            0,
            int((provenance.collected_at - provenance.source_timestamp).total_seconds() * 1000),
        ),
        limitations=provenance.limitations,
        request_id=request_id,
    )


_PERIOD_DAYS = {
    HistoryPeriod.ONE_D: 1,
    HistoryPeriod.FIVE_D: 5,
    HistoryPeriod.ONE_M: 30,
    HistoryPeriod.THREE_M: 90,
    HistoryPeriod.SIX_M: 180,
    HistoryPeriod.ONE_Y: 365,
    HistoryPeriod.FIVE_Y: 1825,
    HistoryPeriod.MAX: 3650,
}


def _period_window(period: HistoryPeriod) -> tuple[datetime, datetime]:
    end_date = datetime.now(UTC).date()
    if period is HistoryPeriod.YTD:
        start_date = date(end_date.year, 1, 1)
    else:
        start_date = end_date - timedelta(days=_PERIOD_DAYS[period] - 1)
    return datetime.combine(start_date, time.min, UTC), datetime.combine(end_date, time.min, UTC)


def _unavailable_history(
    entry: InstrumentCatalogEntry,
    period: HistoryPeriod,
    mode: SeriesMode,
    request_id: str,
) -> PublicHistorySeries:
    return PublicHistorySeries(
        canonical_id=entry.canonical_id,
        symbol=entry.symbol,
        period=period,
        mode=mode,
        adjustment_type="UNADJUSTED",
        currency=entry.currency,
        data_level=DataLevel.DEMO,
        freshness=Freshness.UNAVAILABLE,
        provider="none",
        dataset="none",
        timestamp_collected=datetime.now(UTC),
        limitations=("Nenhum dataset aprovado está disponível para este instrumento.",),
        points=[],
        tabular_fallback=True,
        accessibility={"reduced_motion": True, "smoothed": False},
        unavailable_reason="DATASET_NOT_APPROVED",
        request_id=request_id,
    )


def public_history(
    canonical_id: str,
    period: HistoryPeriod,
    mode: SeriesMode,
    request_id: str,
    adjustment_type: str = "UNADJUSTED",
) -> PublicHistorySeries:
    entry = _find(canonical_id)
    if entry is None:
        raise KeyError(canonical_id)
    if entry.coverage_tier is not CoverageTier.P0_OPERATIONAL:
        return _unavailable_history(entry, period, mode, request_id)
    if get_settings().demo_enabled:
        from app.demo.dataset import DEMO_LIMITATIONS
        from app.demo.read_models import bar_rows, history_points

        rows = bar_rows(canonical_id, period) if adjustment_type == "UNADJUSTED" else []
        if not rows:
            return _unavailable_history(entry, period, mode, request_id)
        latest = rows[-1]
        return PublicHistorySeries(
            canonical_id=canonical_id,
            symbol=entry.symbol,
            period=period,
            mode=mode,
            adjustment_type="UNADJUSTED",
            currency=latest["currency"],
            data_level="DEMO",
            freshness="STALE",
            provider=latest["provider"],
            dataset=latest["dataset"],
            timestamp_official=latest["source_timestamp"],
            timestamp_collected=latest["collected_at"],
            latency_ms=max(
                0, int((latest["collected_at"] - latest["source_timestamp"]).total_seconds() * 1000)
            ),
            limitations=DEMO_LIMITATIONS,
            points=history_points(rows),
            tabular_fallback=True,
            accessibility={"reduced_motion": True, "smoothed": False},
            request_id=request_id,
        )
    start, end = _period_window(period)
    result = _DEMO.historical_bars(canonical_id, start, end)
    provenance = result.provenance
    raw_points = list(result.value)
    base = next((point["close"] for point in raw_points if point.get("close") is not None), None)
    points: list[PublicHistoryPoint] = []
    for raw in raw_points:
        close = raw.get("close")
        value = close if isinstance(close, Decimal) else None
        index = (value / base * Decimal("100")) if value is not None and base else None
        points.append(
            PublicHistoryPoint(
                timestamp=raw["timestamp"],
                session_date=raw["timestamp"].date(),
                open=raw.get("open"),
                high=raw.get("high"),
                low=raw.get("low"),
                close=value,
                volume=raw.get("volume"),
                value=value,
                index_100=index,
            )
        )
    return PublicHistorySeries(
        canonical_id=canonical_id,
        symbol=entry.symbol,
        period=period,
        mode=mode,
        adjustment_type=adjustment_type,
        currency=entry.currency,
        data_level=provenance.data_level,
        freshness=provenance.freshness,
        provider=provenance.provider,
        dataset=provenance.dataset,
        timestamp_official=provenance.source_timestamp,
        timestamp_collected=provenance.collected_at,
        latency_ms=0,
        limitations=provenance.limitations,
        points=points,
        tabular_fallback=True,
        accessibility={"reduced_motion": True, "smoothed": False},
        request_id=request_id,
    )
