from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.contracts import (
    DataLevel,
    EconomicEventImportance,
    EconomicEventStatus,
    EconomicEventValueStatus,
)
from app.main import app
from app.market_data.comparison import normalize_index_100

client = TestClient(app)


def test_calendar_exposes_demo_provenance_and_safe_enums() -> None:
    response = client.get("/api/v1/economic-calendar")
    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    event = body["items"][0]
    assert event["provenance"]["data_level"] == DataLevel.DEMO
    assert event["importance"] in {item.value for item in EconomicEventImportance}
    assert event["status"] in {item.value for item in EconomicEventStatus}
    assert event["value_status"] in {item.value for item in EconomicEventValueStatus}
    assert "recommendation" not in event
    assert "signal" not in event
    assert event["provenance"]["source_timestamp"] <= event["provenance"]["collected_at"]


def test_calendar_enforces_interval_and_timezone() -> None:
    start = date(2026, 1, 1)
    response = client.get(
        "/api/v1/economic-calendar",
        params={
            "date_from": start.isoformat(),
            "date_to": (start + timedelta(days=367)).isoformat(),
        },
    )
    assert response.status_code == 422
    invalid_timezone = client.get(
        "/api/v1/economic-calendar", params={"timezone": "Mars/Olympus"}
    )
    assert invalid_timezone.status_code == 422


def test_calendar_filters_country_and_orders_chronologically() -> None:
    response = client.get("/api/v1/economic-calendar", params={"country": "BR"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert {item["country"] for item in items} == {"BR"}
    assert [item["event_date"] for item in items] == sorted(item["event_date"] for item in items)


def test_calendar_detail_is_factual_and_not_prescriptive() -> None:
    listed = client.get("/api/v1/economic-calendar").json()["items"][0]
    response = client.get(f"/api/v1/economic-calendar/{listed['event_id']}")
    assert response.status_code == 200
    assert not any(
        key in response.json() for key in ("action", "target", "recommendation", "signal")
    )


def test_benchmarks_are_fixed_demo_universe() -> None:
    response = client.get("/api/v1/market-data/benchmarks")
    assert response.status_code == 200
    ids = {item["canonical_id"] for item in response.json()["items"]}
    assert ids == {
        "index.br.b3.ibovespa",
        "rate.br.cdi",
        "index.br.ipca",
        "index.br.ifix",
        "fx.global.usd-brl",
        "index.us.sp500",
        "index.us.nasdaq",
    }
    assert all(item["data_level"] == "DEMO" for item in response.json()["items"])


def test_batch_history_has_explicit_series_limit_and_decimal_index() -> None:
    response = client.post(
        "/api/v1/market-data/history/batch",
        json={"canonical_ids": ["equity.br.b3.petr4"], "period": "5D", "mode": "INDEX_100"},
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["mode"] == "INDEX_100"
    assert response.json()["items"][0]["points"][0]["index_100"] == "100"
    too_many = client.post(
        "/api/v1/market-data/history/batch",
        json={"canonical_ids": [f"equity.br.b3.petr{i}" for i in range(11)], "period": "1D"},
    )
    assert too_many.status_code == 422


def test_batch_quotes_preserve_demo_provenance_and_unique_limit() -> None:
    response = client.post(
        "/api/v1/market-data/quotes/batch",
        json={"canonical_ids": ["equity.br.b3.petr4", "equity.us.nasdaq.aapl"]},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    assert all(item["data_level"] == "DEMO" for item in items)
    assert all(item["provider"] == "demo" for item in items)
    duplicate = client.post(
        "/api/v1/market-data/quotes/batch",
        json={"canonical_ids": ["equity.br.b3.petr4", "equity.br.b3.petr4"]},
    )
    assert duplicate.status_code == 422


def test_benchmark_history_exposes_actual_values_and_index_100() -> None:
    response = client.get(
        "/api/v1/market-data/history/index.br.b3.ibovespa",
        params={"period": "1M", "mode": "INDEX_100"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data_level"] == "DEMO"
    assert body["points"][0]["index_100"] == "100.0000"
    assert body["points"][0]["close"] != body["points"][0]["index_100"]


def test_index_100_rebases_first_available_decimal_without_float() -> None:
    assert normalize_index_100([None, Decimal("12.3456"), Decimal("13.58016")]) == [
        None,
        Decimal("100.0000"),
        Decimal("110.0000"),
    ]


@pytest.mark.parametrize("text", ["compre este ativo", "sinal de compra", "vai subir"])
def test_calendar_lexical_gate_rejects_prescriptive_text(text: str) -> None:
    from app.market_data.economic_calendar import validate_calendar_text

    assert validate_calendar_text(text) is False


def test_calendar_lexical_gate_accepts_factual_text() -> None:
    from app.market_data.economic_calendar import validate_calendar_text

    assert validate_calendar_text("Divulgação mensal do índice de preços") is True
