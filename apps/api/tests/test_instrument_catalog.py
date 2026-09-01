from app.instruments.catalog import (
    FUTURE_CANDIDATE_UNIVERSE,
    MASTER_CATALOG,
    P0_OPERATIONAL_UNIVERSE,
    CatalogStatus,
    CoverageTier,
    DataSupportStatus,
    search_catalog,
)


def test_catalog_separates_operational_and_future_universes() -> None:
    assert P0_OPERATIONAL_UNIVERSE
    assert FUTURE_CANDIDATE_UNIVERSE
    assert not P0_OPERATIONAL_UNIVERSE.intersection(FUTURE_CANDIDATE_UNIVERSE)
    crypto = next(item for item in MASTER_CATALOG if item.symbol == "BTC-USD")
    assert crypto.catalog_status is CatalogStatus.CANDIDATE
    assert crypto.coverage_tier is CoverageTier.FUTURE_REVIEW
    assert crypto.data_support_status is DataSupportStatus.METADATA_ONLY


def test_search_returns_support_level_and_alias_without_changing_identity() -> None:
    result = search_catalog("BTC/USD")
    assert len(result) == 1
    assert result[0].canonical_id == "crypto.global.btc-usd"
    assert search_catalog("PETR4")[0].coverage_tier is CoverageTier.P0_OPERATIONAL


def test_catalog_has_unique_canonical_ids_even_when_symbols_can_repeat() -> None:
    ids = [item.canonical_id for item in MASTER_CATALOG]
    assert len(ids) == len(set(ids))
