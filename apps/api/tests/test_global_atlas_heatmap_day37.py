"""Day 37 (ADR-019): tabular Global Atlas from the catalog and the basic P0 heatmap."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

import app.demo.read_models as read_models
import app.instruments.catalog as catalog
import app.market_data.public_market_data as public_market_data
from app.core.config import Settings
from app.instruments.catalog import MASTER_CATALOG, InstrumentCatalogEntry
from app.main import app
from app.market_data.heatmap import HEATMAP_INSTRUMENT_TYPES

client = TestClient(app)
VOLATILE = {"request_id", "timestamp_collected", "timestamp_official", "latency_ms"}


def _without(item: dict) -> dict:
    return {key: value for key, value in item.items() if key not in VOLATILE}


def test_instruments_lists_the_catalog_with_location_metadata() -> None:
    body = client.get("/api/v1/instruments", params={"limit": 100}).json()
    ids = [item["canonical_id"] for item in body["items"]]
    assert ids == [entry.canonical_id for entry in reversed(MASTER_CATALOG)], "created_at desc"
    for item, entry in zip(body["items"], reversed(MASTER_CATALOG), strict=True):
        assert (item["exchange"], item["country"], item["region"], item["timezone"]) == (
            entry.exchange,
            entry.country,
            entry.region,
            entry.timezone,
        )
        assert "price" not in item, "the atlas is metadata, never a quote"
    assert body["meta"]["next_offset"] is None


def test_instruments_sort_order_and_pagination() -> None:
    symbols = sorted(entry.symbol.casefold() for entry in MASTER_CATALOG)
    asc = client.get("/api/v1/instruments", params={"sort": "symbol", "order": "asc"}).json()
    assert [item["symbol"].casefold() for item in asc["items"]] == symbols
    first = client.get("/api/v1/instruments", params={"limit": 2, "sort": "symbol", "order": "asc"})
    assert first.json()["meta"]["next_offset"] == 2
    assert client.get("/api/v1/instruments", params={"sort": "price"}).status_code == 422


def test_search_keeps_its_items_and_gains_the_same_metadata() -> None:
    item = client.get("/api/v1/instruments/search", params={"q": "PETR4"}).json()["items"][0]
    assert item["canonical_id"] == "equity.br.b3.petr4"
    assert (item["exchange"], item["region"], item["timezone"]) == ("B3", "BR", "America/Sao_Paulo")


def test_heatmap_tiles_are_the_public_quotes_and_declare_what_is_missing() -> None:
    body = client.get("/api/v1/market-data/heatmap").json()
    assert (body["grouping"], body["sizing"], body["color_basis"]) == (
        "INSTRUMENT_TYPE",
        "EQUAL_AREA",
        "DIRECTION_VS_PREVIOUS_CLOSE",
    )
    assert any("Setor indisponível" in text for text in body["limitations"])
    assert any("Valor de mercado indisponível" in text for text in body["limitations"])
    tiles = [tile for group in body["groups"] for tile in group["tiles"]]
    assert {group["group"] for group in body["groups"]} <= set(HEATMAP_INSTRUMENT_TYPES)
    assert "index" not in {tile["asset_type"].lower() for tile in tiles}
    for tile in tiles:
        quote = client.get(f"/api/v1/market-data/quotes/{tile['canonical_id']}").json()
        assert _without(tile) == _without(quote)
    states = {tile["symbol"]: tile["freshness"] for tile in tiles}
    assert states["MXRF11"] == "UNAVAILABLE", "no approved dataset, no value"
    assert all(tile["change"] is None for tile in tiles), "no previous close outside DEMO"


def _demo_entry(symbol: str, kind: str) -> InstrumentCatalogEntry:
    return InstrumentCatalogEntry(
        canonical_id=f"demo.{kind.lower()}.{symbol.lower()}",
        symbol=symbol,
        display_symbol=symbol,
        name=f"{symbol} DEMO",
        instrument_type=kind,
        exchange="DEMO",
        country="BR",
        region="DEMO",
        currency="BRL",
        timezone="UTC",
        catalog_status="CANDIDATE",
        coverage_tier="P0_CATALOG",
        data_support_status="METADATA_ONLY",
    )


def test_demo_heatmap_computes_change_from_the_previous_close(monkeypatch) -> None:
    entries = (_demo_entry("MPXA3", "EQUITY"), _demo_entry("MPXB3", "EQUITY"))
    entries += (_demo_entry("MPTECH", "INDEX"),)
    closes = {
        "demo.equity.mpxa3": [Decimal("106"), Decimal("108")],
        "demo.equity.mpxb3": [Decimal("58.5"), Decimal("58")],
        "demo.index.mptech": [Decimal("1020"), Decimal("1030")],
    }
    stamp = datetime(2026, 1, 30, 20, tzinfo=UTC)

    def quote_row(canonical_id: str) -> dict:
        return {
            "price": closes[canonical_id][-1],
            "currency": "BRL",
            "data_level": "DEMO",
            "freshness": "STALE",
            "provider": "demo",
            "dataset": "demo-day24",
            "source_timestamp": stamp,
            "collected_at": stamp,
        }

    settings = Settings(demo_enabled=True)
    monkeypatch.setattr(catalog, "get_settings", lambda: settings)
    monkeypatch.setattr(public_market_data, "get_settings", lambda: settings)
    monkeypatch.setattr(read_models, "catalog_entries", lambda: entries)
    monkeypatch.setattr(read_models, "quote_row", quote_row)
    monkeypatch.setattr(
        read_models, "bar_rows", lambda canonical_id: [{"close": c} for c in closes[canonical_id]]
    )

    body = client.get("/api/v1/market-data/heatmap").json()
    assert [group["group"] for group in body["groups"]] == ["EQUITY"], "indices are references"
    tiles = {tile["symbol"]: tile for tile in body["groups"][0]["tiles"]}
    assert Decimal(tiles["MPXA3"]["change"]) == Decimal("2")
    assert Decimal(tiles["MPXB3"]["change"]) == Decimal("-0.5")
    assert Decimal(tiles["MPXB3"]["change_percent"]) == Decimal("-0.5") / Decimal("58.5") * 100
    assert {tile["data_level"] for tile in tiles.values()} == {"DEMO"}
