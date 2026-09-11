"""Fixed benchmark universe and synthetic comparison series."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.contracts import (
    BenchmarkItem,
    DataLevel,
    Freshness,
    HistoryPeriod,
    PublicHistoryPoint,
    PublicHistorySeries,
    SeriesMode,
)
from app.market_data.comparison import normalize_index_100

UTC = timezone.utc

_BENCHMARKS: tuple[tuple[str, str, str, str, Decimal], ...] = (
    ("index.br.b3.ibovespa", "IBOV", "Ibovespa", "BRL", Decimal("100000")),
    ("rate.br.cdi", "CDI", "CDI", "BRL", Decimal("10.50")),
    ("index.br.ipca", "IPCA", "IPCA", "BRL", Decimal("4.20")),
    ("index.br.ifix", "IFIX", "Índice de Fundos Imobiliários", "BRL", Decimal("3200")),
    ("fx.global.usd-brl", "USD/BRL", "Dólar americano / Real", "BRL", Decimal("5.10")),
    ("index.us.sp500", "S&P 500", "S&P 500", "USD", Decimal("5200")),
    ("index.us.nasdaq", "NASDAQ", "Nasdaq Composite", "USD", Decimal("16300")),
)


def benchmark_ids() -> frozenset[str]:
    return frozenset(item[0] for item in _BENCHMARKS)


def benchmark_items() -> list[BenchmarkItem]:
    collected = datetime.now(UTC)
    return [
        BenchmarkItem(
            canonical_id=canonical_id,
            symbol=symbol,
            name=name,
            currency=currency,
            value=value,
            change_percent=Decimal("0.00"),
            data_level=DataLevel.DEMO,
            freshness=Freshness.STALE,
            source="market-pulse-demo",
            dataset="demo-benchmarks",
            timestamp_official=collected - timedelta(days=1),
            timestamp_collected=collected,
            limitations=("Benchmark sintético DEMO; provider e licença permanecem bloqueados.",),
        )
        for canonical_id, symbol, name, currency, value in _BENCHMARKS
    ]


def benchmark_series(
    canonical_id: str,
    period: HistoryPeriod,
    mode: SeriesMode,
    request_id: str,
) -> PublicHistorySeries | None:
    benchmark = next((item for item in _BENCHMARKS if item[0] == canonical_id), None)
    if benchmark is None:
        return None
    _, symbol, _, currency, latest = benchmark
    collected = datetime.now(UTC)
    raw_values = [latest - Decimal("2.0"), latest - Decimal("1.0"), latest - Decimal("0.5"), latest]
    timestamps = [collected - timedelta(days=offset) for offset in (3, 2, 1, 0)]
    indexes = normalize_index_100(raw_values)
    points = [
        PublicHistoryPoint(
            timestamp=timestamp,
            session_date=timestamp.date(),
            close=value,
            value=value,
            index_100=index,
        )
        for timestamp, value, index in zip(timestamps, raw_values, indexes, strict=True)
    ]
    return PublicHistorySeries(
        canonical_id=canonical_id,
        symbol=symbol,
        period=period,
        mode=mode,
        adjustment_type="UNADJUSTED",
        currency=currency,
        data_level=DataLevel.DEMO,
        freshness=Freshness.STALE,
        provider="market-pulse-demo",
        dataset="demo-benchmarks",
        timestamp_official=timestamps[-1],
        timestamp_collected=collected,
        latency_ms=0,
        limitations=("Benchmark sintético DEMO; não representa índice ou cotação oficial.",),
        points=points,
        tabular_fallback=True,
        accessibility={"reduced_motion": True, "smoothed": False},
        request_id=request_id,
    )
