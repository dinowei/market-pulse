import pytest
from fastapi.testclient import TestClient

from app.instruments.catalog import (
    FUTURE_CANDIDATE_UNIVERSE,
    MASTER_CATALOG,
    P0_OPERATIONAL_UNIVERSE,
    CatalogStatus,
    CoverageTier,
    DataSupportStatus,
    search_catalog,
)
from app.main import app

client = TestClient(app)


def test_catalog_separates_operational_and_future_universes() -> None:
    assert P0_OPERATIONAL_UNIVERSE
    assert FUTURE_CANDIDATE_UNIVERSE
    assert not P0_OPERATIONAL_UNIVERSE.intersection(FUTURE_CANDIDATE_UNIVERSE)
    crypto = next(item for item in MASTER_CATALOG if item.symbol == "BTC-USD")
    assert crypto.catalog_status is CatalogStatus.CANDIDATE
    # ADR-029: priced only in the owner's private session (ADR-027), so P1 and pending.
    assert crypto.coverage_tier is CoverageTier.P1
    assert crypto.data_support_status is DataSupportStatus.PROVIDER_PENDING


def test_search_returns_support_level_and_alias_without_changing_identity() -> None:
    result = search_catalog("BTC/USD")
    assert len(result) == 1
    assert result[0].canonical_id == "crypto.global.btc-usd"
    assert search_catalog("PETR4")[0].coverage_tier is CoverageTier.P0_OPERATIONAL


def test_catalog_has_unique_canonical_ids_even_when_symbols_can_repeat() -> None:
    ids = [item.canonical_id for item in MASTER_CATALOG]
    assert len(ids) == len(set(ids))


def test_no_catalog_entry_is_priced_without_an_approved_dataset() -> None:
    # H-31: a price appears only for the operational universe, and even there it is DEMO
    # (no provider is approved). Every other entry stays UNAVAILABLE, never tradable.
    assert not any(
        entry.data_support_status is DataSupportStatus.DATA_AVAILABLE_APPROVED
        for entry in MASTER_CATALOG
    )
    # One listing for the support states: one search per entry would exceed the per-IP
    # rate limit now that the catalog is wider (ADR-029).
    listed = client.get("/api/v1/instruments", params={"limit": 100}).json()["items"]
    states = {item["canonical_id"]: item["support_state"] for item in listed}
    for entry in MASTER_CATALOG:
        quote = client.get(f"/api/v1/market-data/quotes/{entry.canonical_id}").json()
        if entry.canonical_id in P0_OPERATIONAL_UNIVERSE:
            assert quote["data_level"] == "DEMO", entry.canonical_id
        else:
            assert (quote["freshness"], quote["price"]) == ("UNAVAILABLE", None), entry.symbol
        expected = (
            "P0_OPERATIONAL"
            if entry.canonical_id in P0_OPERATIONAL_UNIVERSE
            else "CANDIDATE_FUTURE"
        )
        assert states[entry.canonical_id] == expected, entry.symbol


@pytest.mark.parametrize("canonical_id", ["equity.br.b3.vale3", "equity.br.b3.cmin3"])
def test_named_b3_equities_are_never_priced_outside_the_owner_session(canonical_id: str) -> None:
    # ADR-023 named them with metadata only; ADR-029 prices them in the owner's session alone.
    entry = next(item for item in MASTER_CATALOG if item.canonical_id == canonical_id)
    assert entry.canonical_id not in P0_OPERATIONAL_UNIVERSE
    assert entry.data_support_status is DataSupportStatus.PROVIDER_PENDING
    quote = client.get(f"/api/v1/market-data/quotes/{canonical_id}").json()
    assert (quote["freshness"], quote["price"]) == ("UNAVAILABLE", None)
    assert quote["unavailable_reason"] == "DATASET_NOT_APPROVED"
    history = client.get(
        f"/api/v1/market-data/history/{canonical_id}", params={"period": "1M"}
    ).json()
    assert history["freshness"] == "UNAVAILABLE"
    assert not any(point.get("close") for point in history["points"])
