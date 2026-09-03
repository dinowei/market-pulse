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
from app.instruments.catalog import (
    MASTER_CATALOG,
    CatalogStatus,
    CoverageTier,
    DataSupportStatus,
    InstrumentCatalogEntry,
)
from app.providers.demo import DemoProvider
from app.providers.models import DataLevel, Freshness

UTC = timezone.utc
_DEMO = DemoProvider()


def _find(canonical_id: str) -> InstrumentCatalogEntry | None:
    return next((entry for entry in MASTER_CATALOG if entry.canonical_id == canonical_id), None)


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
            int(
                (provenance.collected_at - provenance.source_timestamp).total_seconds()
                * 1000
            ),
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
