"""Day 35: aligned M4 for multi-series comparison keeps every series comparable."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

import app.routers as routers
from app.contracts import BatchHistoryRequest, PublicHistoryPoint, PublicHistorySeries
from app.main import app
from app.market_data.downsampling import MAX_MAX_POINTS, MIN_MAX_POINTS, downsample_aligned

START = datetime(2016, 1, 4, 20, tzinfo=UTC)


def _points(values: list[Decimal]) -> list[PublicHistoryPoint]:
    base = values[0]
    return [
        PublicHistoryPoint(
            timestamp=START + timedelta(days=i),
            session_date=(START + timedelta(days=i)).date(),
            close=value,
            value=value,
            index_100=value / base * Decimal("100"),
        )
        for i, value in enumerate(values)
    ]


def _asset(count: int) -> list[Decimal]:
    values = [Decimal("40") + Decimal((i * 13) % 17) / Decimal("10") for i in range(count)]
    values[count // 4] = Decimal("90")  # spike only in the asset
    return values


def _benchmark(count: int) -> list[Decimal]:
    values = [Decimal("100000") + Decimal((i * 7) % 29) * Decimal("10") for i in range(count)]
    values[3 * count // 4] = Decimal("80000")  # drop only in the benchmark
    return values


def test_aligned_series_share_the_same_instants_and_keep_their_own_extremes() -> None:
    asset, benchmark = _points(_asset(2600)), _points(_benchmark(2600))
    reduced_asset, reduced_benchmark = downsample_aligned([asset, benchmark], 400)
    assert reduced_asset.applied and reduced_benchmark.applied
    asset_instants = [p.timestamp for p in reduced_asset.points]
    assert asset_instants == [p.timestamp for p in reduced_benchmark.points]
    assert asset[2600 // 4].timestamp in asset_instants, "asset spike survives"
    assert benchmark[3 * 2600 // 4].timestamp in asset_instants, "benchmark drop survives"
    assert asset[0].timestamp == asset_instants[0], "INDEX_100 base point is kept"
    assert len(asset_instants) <= 2 * 400


def test_short_comparisons_are_untouched() -> None:
    asset, benchmark = _points(_asset(300)), _points(_benchmark(300))
    results = downsample_aligned([asset, benchmark], 500)
    assert [r.applied for r in results] == [False, False]
    assert results[0].points == asset and results[1].points == benchmark


def test_contract_bounds_match_the_downsampling_module() -> None:
    field = BatchHistoryRequest.model_fields["max_points"]
    bounds = {type(item).__name__: item for item in field.metadata}
    assert bounds["Ge"].ge == MIN_MAX_POINTS and bounds["Le"].le == MAX_MAX_POINTS


def _series(canonical_id: str, values: list[Decimal]) -> PublicHistorySeries:
    now = datetime.now(UTC)
    return PublicHistorySeries(
        canonical_id=canonical_id,
        symbol=canonical_id.rsplit(".", 1)[-1].upper(),
        period="MAX",
        mode="INDEX_100",
        adjustment_type="UNADJUSTED",
        currency="BRL",
        data_level="DEMO",
        freshness="STALE",
        provider="demo",
        dataset="demo-history",
        timestamp_official=now,
        timestamp_collected=now,
        latency_ms=0,
        points=_points(values),
        accessibility={"reduced_motion": True, "smoothed": False},
        request_id="test",
    )


def test_batch_endpoint_reduces_only_on_request_and_keeps_alignment(monkeypatch) -> None:
    long_series = {
        "equity.br.b3.petr4": _series("equity.br.b3.petr4", _asset(2600)),
        "index.br.b3.ibovespa": _series("index.br.b3.ibovespa", _benchmark(2600)),
    }
    monkeypatch.setattr(routers, "benchmark_series", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        routers, "public_history", lambda canonical_id, *a, **k: long_series[canonical_id]
    )
    client = TestClient(app)
    body = {"canonical_ids": list(long_series), "period": "MAX", "mode": "INDEX_100"}

    full = client.post("/api/v1/market-data/history/batch", json=body).json()["items"]
    assert [len(item["points"]) for item in full] == [2600, 2600]
    assert all(item["downsampling"] is None for item in full)

    reduced = client.post(
        "/api/v1/market-data/history/batch", json={**body, "max_points": 400}
    ).json()["items"]
    instants = [[p["timestamp"] for p in item["points"]] for item in reduced]
    assert instants[0] == instants[1]
    for item in reduced:
        assert item["downsampling"]["original_points"] == 2600
        assert item["downsampling"]["returned_points"] == len(item["points"])
    assert (
        client.post(
            "/api/v1/market-data/history/batch", json={**body, "max_points": 10}
        ).status_code
        == 422
    )
