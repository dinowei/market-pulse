"""Day 31: M4 display downsampling preserves first, last, extremes and gaps (ADR-013)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import app.routers as routers
from app.contracts import PublicHistoryPoint, PublicHistorySeries
from app.main import app
from app.market_data.downsampling import MAX_MAX_POINTS, MIN_MAX_POINTS, downsample_m4

START = datetime(2016, 1, 4, 20, tzinfo=UTC)


def _series(values: list[Decimal | None], gaps: set[int] = frozenset()) -> list[PublicHistoryPoint]:
    base = next(value for value in values if value is not None)
    points = []
    for index, value in enumerate(values):
        timestamp = START + timedelta(days=index)
        points.append(
            PublicHistoryPoint(
                timestamp=timestamp,
                session_date=timestamp.date(),
                close=value,
                value=value,
                index_100=None if value is None else value / base * Decimal("100"),
                is_gap=index in gaps,
            )
        )
    return points


def _wave(count: int) -> list[Decimal]:
    # Deterministic, irregular Decimal series with a single spike and a V-shaped drawdown.
    values = [Decimal("50") + Decimal((index * 37) % 23) / Decimal("10") for index in range(count)]
    values[count // 3] = Decimal("99.99")  # isolated spike
    for offset in range(-40, 41):
        values[2 * count // 3 + offset] = Decimal("20") + Decimal(abs(offset)) / Decimal("4")
    return values


def test_short_series_is_returned_untouched() -> None:
    points = _series(_wave(200))
    result = downsample_m4(points, 500)
    assert result.applied is False
    assert result.points == points
    assert result.original_points == 200


def test_output_is_an_ordered_exact_subset_with_bounded_size() -> None:
    points = _series(_wave(2600))
    result = downsample_m4(points, 400)
    assert result.applied is True
    assert result.original_points == 2600
    assert len(result.points) <= 400
    timestamps = [point.timestamp for point in result.points]
    assert timestamps == sorted(timestamps) and len(set(timestamps)) == len(timestamps)
    originals = {point.timestamp: point for point in points}
    for point in result.points:
        assert point is originals[point.timestamp], "no point may be created or rebuilt"


def test_first_last_global_and_bucket_extremes_survive() -> None:
    values = _wave(2600)
    points = _series(values)
    result = downsample_m4(points, 400)
    kept = {point.timestamp for point in result.points}
    assert points[0].timestamp in kept and points[-1].timestamp in kept
    assert points[values.index(max(values))].timestamp in kept, "isolated spike must survive"
    assert points[values.index(min(values))].timestamp in kept, "drawdown bottom must survive"
    buckets = 400 // 4
    for bucket in range(buckets):
        start, end = bucket * 2600 // buckets, (bucket + 1) * 2600 // buckets
        window = range(start, end)
        assert points[min(window, key=lambda i: (values[i], i))].timestamp in kept
        assert points[max(window, key=lambda i: (values[i], -i))].timestamp in kept


def test_every_gap_and_valueless_point_is_kept() -> None:
    values: list[Decimal | None] = list(_wave(2600))
    gaps = {5, 777, 1500, 2599}
    for index in gaps:
        values[index] = None
    points = _series(values, gaps=gaps)
    result = downsample_m4(points, 200)
    kept = {point.timestamp for point in result.points}
    assert all(points[index].timestamp in kept for index in gaps)
    assert all(point.value is None for point in result.points if point.is_gap)


def test_index_100_and_decimal_values_are_not_recomputed() -> None:
    points = _series(_wave(2600))
    result = downsample_m4(points, 256)
    for point in result.points:
        assert isinstance(point.value, Decimal)
        assert point.index_100 == point.value / points[0].value * Decimal("100")


def test_result_is_deterministic_with_ties() -> None:
    points = _series([Decimal("10")] * 3000)
    first = downsample_m4(points, 128)
    second = downsample_m4(points, 128)
    assert [p.timestamp for p in first.points] == [p.timestamp for p in second.points]


@pytest.mark.parametrize("max_points", [MIN_MAX_POINTS - 1, MAX_MAX_POINTS + 1, 0, -5])
def test_out_of_range_max_points_is_rejected(max_points: int) -> None:
    with pytest.raises(ValueError, match="max_points"):
        downsample_m4(_series(_wave(300)), max_points)


def _long_series(request_id: str = "test") -> PublicHistorySeries:
    now = datetime.now(UTC)
    return PublicHistorySeries(
        canonical_id="equity.br.b3.petr4",
        symbol="PETR4",
        period="MAX",
        mode="PRICE",
        adjustment_type="UNADJUSTED",
        currency="BRL",
        data_level="DEMO",
        freshness="STALE",
        provider="demo",
        dataset="demo-history",
        timestamp_official=now,
        timestamp_collected=now,
        latency_ms=0,
        limitations=("Demonstração sintética; não representa mercado real.",),
        points=_series(_wave(2600)),
        accessibility={"reduced_motion": True, "smoothed": False},
        request_id=request_id,
    )


def test_history_endpoint_reduces_only_on_request_and_discloses_it(monkeypatch) -> None:
    monkeypatch.setattr(routers, "benchmark_series", lambda *args, **kwargs: None)
    monkeypatch.setattr(routers, "public_history", lambda *args, **kwargs: _long_series())
    client = TestClient(app)
    url = "/api/v1/market-data/history/equity.br.b3.petr4?period=MAX"

    full = client.get(url).json()
    assert len(full["points"]) == 2600 and full["downsampling"] is None

    reduced = client.get(url + "&max_points=500").json()
    assert reduced["downsampling"] == {
        "method": "M4",
        "max_points": 500,
        "original_points": 2600,
        "returned_points": len(reduced["points"]),
        "preserved": ["FIRST", "LAST", "MIN", "MAX", "GAPS"],
        "basis": "value",
    }
    assert len(reduced["points"]) <= 500
    full_by_ts = {point["timestamp"]: point for point in full["points"]}
    assert all(full_by_ts[point["timestamp"]] == point for point in reduced["points"])
    assert reduced["data_level"] == "DEMO" and reduced["freshness"] == "STALE"
    assert reduced["accessibility"]["smoothed"] is False

    assert client.get(url + f"&max_points={MIN_MAX_POINTS - 1}").status_code == 422
    assert client.get(url + f"&max_points={MAX_MAX_POINTS + 1}").status_code == 422
