
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_public_catalog_supports_all_search_modes_without_prices():
    for query in ("equity.br.b3.petr4", "PETR4", "Petrobras", "BTC/USD"):
        response = client.get("/api/v1/instruments/search", params={"q": query})
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert "price" not in item
            assert item["canonical_id"]


def test_public_quote_demo_is_explicit_and_provenance_complete():
    response = client.get("/api/v1/market-data/quotes/equity.br.b3.petr4")
    assert response.status_code == 200
    body = response.json()
    assert body["data_level"] == "DEMO"
    assert body["freshness"] == "STALE"
    assert body["provider"] == "demo"
    assert body["dataset"] == "demo-quotes"
    assert body["timestamp_official"] and body["timestamp_collected"]
    assert body["latency_ms"] >= 0
    assert isinstance(body["price"], str)
    assert body["request_id"]


def test_public_quote_unknown_and_candidate_fail_closed_without_provider_call():
    unknown = client.get("/api/v1/market-data/quotes/equity.br.b3.unknown")
    assert unknown.status_code == 404
    assert unknown.headers["content-type"].startswith("application/problem+json")
    candidate = client.get("/api/v1/market-data/quotes/crypto.global.btc-usd")
    assert candidate.status_code == 200
    assert candidate.json()["freshness"] == "UNAVAILABLE"
    assert candidate.json()["unavailable_reason"] == "DATASET_NOT_APPROVED"


def test_public_history_accepts_all_periods_and_strict_modes():
    for period in ("1D", "5D", "1M", "3M", "6M", "YTD", "1A", "5A", "MAX"):
        response = client.get(
            "/api/v1/market-data/history/equity.br.b3.petr4",
            params={"period": period, "mode": "PRICE"},
        )
        assert response.status_code == 200
        assert response.json()["period"] == period
    invalid = client.get(
        "/api/v1/market-data/history/equity.br.b3.petr4",
        params={"period": "2D", "mode": "PRICE"},
    )
    assert invalid.status_code == 422


def test_public_history_index_100_preserves_real_price_and_tabular_fallback():
    response = client.get(
        "/api/v1/market-data/history/equity.br.b3.petr4",
        params={"period": "5D", "mode": "INDEX_100"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "INDEX_100"
    assert body["tabular_fallback"] is True
    assert body["accessibility"]["reduced_motion"] is True
    assert body["accessibility"]["smoothed"] is False
    assert body["points"]
    assert body["points"][0]["index_100"] == "100"
    assert body["points"][0]["value"] == body["points"][0]["close"]


def test_public_history_has_no_synthetic_interpolation_and_unavailable_is_controlled():
    response = client.get(
        "/api/v1/market-data/history/crypto.global.btc-usd",
        params={"period": "1D", "mode": "PRICE"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["freshness"] == "UNAVAILABLE"
    assert body["points"] == []
    assert body["unavailable_reason"] == "DATASET_NOT_APPROVED"
