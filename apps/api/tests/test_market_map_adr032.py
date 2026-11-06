from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.market_data import asset_profile, live_data, market_map
from app.market_data.live_data import Snapshot
from app.providers import vendors
from app.providers.models import Freshness


def test_brapi_list_keeps_declared_fields_and_drops_bad_rows():
    rows = vendors.brapi_list(
        {
            "stocks": [
                {
                    "stock": "PETR4",
                    "name": "Petrobras",
                    "close": Decimal("45.95"),
                    "change": Decimal("-2.48"),
                    "volume": 10,
                    "market_cap": 647681842186,
                    "sector": "Energy Minerals",
                    "type": "stock",
                },
                {"stock": "BAD", "close": 0},
                {"close": 1},
            ]
        }
    )
    assert [row["symbol"] for row in rows] == ["PETR4"]
    assert rows[0]["change_percent"] == "-2.48"
    assert rows[0]["market_cap"] == "647681842186"


def test_massive_grouped_reads_a_day_without_results_as_empty():
    assert vendors.massive_grouped({"results": None}) == {}
    bars = vendors.massive_grouped({"results": [{"T": "AAPL", "c": Decimal("344.17"), "v": 7}, {"T": "X"}]})
    assert bars["AAPL"]["close"] == "344.17"
    assert "X" not in bars


def _br_snapshot():
    row = {
        "symbol": "PETR4",
        "name": "Petrobras",
        "price": "45.95",
        "change_percent": "-2.48",
        "volume": "10",
        "market_cap": "100",
        "sector": "Energy Minerals",
        "type": "stock",
    }
    fund = {**row, "symbol": "MXRF11", "market_cap": None, "type": "fund"}
    from datetime import UTC, datetime

    return Snapshot(
        {"session": "2026-11-05", "rows": {"PETR4": row, "MXRF11": fund}},
        Freshness.FRESH,
        datetime.now(UTC),
    )


def test_br_map_uses_source_sector_and_market_value(monkeypatch):
    monkeypatch.setattr(live_data, "br_snapshot", _br_snapshot)
    result = market_map.real_market_map("BR", "req")
    assert result.sizing == "MARKET_CAP" and result.is_demo is False
    assert [sector.sector for sector in result.sectors] == ["Petróleo, Gás e Energia"]
    tile = result.sectors[0].tiles[0]
    assert tile.symbol == "PETR4" and tile.size_value == Decimal(100)
    assert tile.canonical_id == "equity.br.b3.petr4"


def test_us_map_sizes_by_traded_value_and_keeps_unknown_change_null(monkeypatch):
    from datetime import UTC, datetime

    rows = {
        "AAPL": {"close": "10", "volume": "5", "previous_close": "8"},
        "MSFT": {"close": "10", "volume": "1", "previous_close": None},
    }
    snapshot = Snapshot({"session": "2026-11-04", "rows": rows}, Freshness.STALE, datetime.now(UTC))
    monkeypatch.setattr(live_data, "_shared_us_snapshot", lambda: snapshot)
    result = market_map.real_market_map("US", "req")
    tiles = {tile.symbol: tile for tile in result.sectors[0].tiles}
    assert result.sizing == "TRADED_VALUE" and result.freshness == "STALE"
    assert tiles["AAPL"].change_percent == Decimal(25)
    assert tiles["AAPL"].size_value == Decimal(50)
    assert tiles["MSFT"].change_percent is None


def test_no_snapshot_means_empty_with_reason(monkeypatch):
    monkeypatch.setattr(live_data, "br_snapshot", lambda: None)
    result = market_map.real_market_map("BR", "req")
    assert result.sectors == [] and result.unavailable_reason == "UNAVAILABLE"


def test_bulk_quote_reads_percent_from_list_and_never_invents_a_time(monkeypatch):
    monkeypatch.setattr(live_data, "br_snapshot", _br_snapshot)
    result = live_data.bulk_quote("equity.br.b3.petr4")
    assert result.value.change_percent == Decimal("-2.48")
    assert result.value.source_timestamp is None
    assert result.value.session_date.isoformat() == "2026-11-05"
    assert live_data.bulk_quote("fx.global.usd-brl") is None


def test_profile_copies_facts_with_source_and_scales_percent_once(monkeypatch):
    sections = {
        "brapi": {
            "results": [
                {
                    "currency": "BRL",
                    "marketCap": 100,
                    "fiftyTwoWeekHigh": Decimal("50.5"),
                    "priceEarnings": None,
                    "summaryProfile": {
                        "sectorDisp": "Energia",
                        "longBusinessSummary": "Resumo.",
                        "website": "http://inseguro.example",
                    },
                    "defaultKeyStatistics": {"profitMargins": Decimal("0.25")},
                    "dividendsData": {
                        "cashDividends": [
                            {
                                "label": "JCP",
                                "rate": Decimal("0.2"),
                                "exDate": "2026-08-24T03:00:00.000Z",
                                "paymentDate": "2026-12-21T03:00:00.000Z",
                            },
                            {"label": "ruim", "rate": 0},
                        ]
                    },
                }
            ]
        }
    }
    monkeypatch.setattr(live_data, "live_profile", lambda _id: sections)
    profile = asset_profile.real_asset_profile("equity.br.b3.petr4", "req")
    facts = {fact.key: fact for fact in profile.facts}
    assert facts["profitMargins"].value == "25.00"
    assert facts["marketCap"].source == "brapi"
    assert "priceEarnings" not in facts
    assert profile.website is None
    assert [item.label for item in profile.dividends] == ["JCP"]
    assert profile.dividends[0].ex_date.isoformat() == "2026-08-24"


def test_routes_keep_visitors_out_of_real_data(monkeypatch):
    client = TestClient(app)
    settings = SimpleNamespace(real_data_providers=("brapi",))
    monkeypatch.setattr("app.routers.get_settings", lambda: settings)
    monkeypatch.setattr("app.routers._signed_in", lambda _request: False)
    response = client.get("/api/v1/market-data/market-map?market=BR")
    assert response.status_code == 200
    assert response.json()["unavailable_reason"] == "SESSION_REQUIRED"
    assert response.json()["sectors"] == []
    assert response.headers["cache-control"] == "private, no-store"
    profile = client.get("/api/v1/market-data/profile/equity.br.b3.petr4")
    assert profile.json()["unavailable_reason"] == "SESSION_REQUIRED"
    assert client.get("/api/v1/market-data/profile/nao.existe").status_code == 404


def test_news_with_a_recommendation_never_reaches_the_screen():
    article = {
        "publisher": {"name": "Fonte"},
        "published_utc": "2026-11-05T10:00:00Z",
        "article_url": "https://example.com/a",
    }
    items = vendors.massive_news(
        {
            "results": [
                {**article, "title": "Should You Buy the Dip?"},
                {**article, "title": "Ações caem", "description": "A compelling buy for many."},
                {**article, "title": "Brazil stocks fell", "description": "After the election."},
            ]
        }
    )
    assert [item["title"] for item in items] == ["Brazil stocks fell"]
    assert items[0]["description"] == "After the election."
