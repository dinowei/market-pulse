from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.contracts import HistoricalSeries, QuoteContract, SeriesMode
from app.instruments.catalog import (
    CatalogStatus,
    InstrumentCatalogEntry,
    search_catalog,
)
from app.main import app
from app.market_data.cache import CacheEnvelope, MemoryCacheBackend
from app.market_data.freshness import WeekdayMarketCalendar, compute_freshness
from app.providers.candidate_adapters import BrapiAdapter, ProviderHttpResponse
from app.providers.models import DataLevel, Freshness, ProviderDatasetRef, ProviderProvenance, ProviderResult


client = TestClient(app)
UTC = timezone.utc


def _provenance() -> ProviderProvenance:
    now = datetime(2026, 9, 2, 12, tzinfo=UTC)
    return ProviderProvenance(
        provider="demo",
        dataset="demo-quotes",
        source="demo",
        source_timestamp=now,
        collected_at=now,
        data_level=DataLevel.DEMO,
        freshness=Freshness.STALE,
        currency="BRL",
        latency_ms=12,
    )


def test_http_search_uses_catalog_identity_and_exposes_support_state():
    response = client.get("/api/v1/instruments/search", params={"q": "BTC/USD"})
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["canonical_id"] == "crypto.global.btc-usd"
    assert item["support_state"] == "CANDIDATE_FUTURE"


def test_catalog_search_matches_canonical_id_and_ticker_is_not_identity():
    result = search_catalog("equity.br.b3.petr4")
    assert result[0].canonical_id == "equity.br.b3.petr4"
    assert result[0].symbol == "PETR4"
    with pytest.raises(ValueError):
        InstrumentCatalogEntry(
            canonical_id="equity.br.b3.fake",
            symbol="FAKE",
            display_symbol="FAKE",
            name="Fake fund",
            instrument_type="MUTUAL_FUND",
            currency="BRL",
            timezone="America/Sao_Paulo",
            catalog_status=CatalogStatus.ACTIVE,
            coverage_tier="P0_OPERATIONAL",
            data_support_status="PROVIDER_PENDING",
        )


def test_same_ticker_can_have_distinct_canonical_ids():
    br = InstrumentCatalogEntry(
        canonical_id="equity.br.b3.same",
        symbol="SAME",
        display_symbol="SAME",
        name="Same BR",
        instrument_type="EQUITY",
        currency="BRL",
        timezone="America/Sao_Paulo",
        catalog_status="ACTIVE",
        coverage_tier="P0_CATALOG",
        data_support_status="METADATA_ONLY",
    )
    us = br.model_copy(
        update={
            "canonical_id": "equity.us.nasdaq.same",
            "currency": "USD",
            "timezone": "America/New_York",
        }
    )
    assert br.canonical_id != us.canonical_id and br.symbol == us.symbol


def test_public_quote_route_fails_closed_without_approved_dataset():
    response = client.get("/api/v1/market-data/quotes/latest")
    assert response.status_code == 200
    assert response.json()["status"] == "UNAVAILABLE"


def test_financial_contracts_require_provenance_and_latency():
    with pytest.raises(ValueError):
        QuoteContract(
            instrument_id="equity.br.b3.petr4",
            price=Decimal("10"),
            currency="BRL",
            data_level=DataLevel.DEMO,
            freshness=Freshness.STALE,
            source="demo",
            source_timestamp=None,
            collected_at=None,
            dataset="demo-quotes",
            latency_ms=1,
        )
    series = HistoricalSeries(
        instrument_id="equity.br.b3.petr4",
        currency="BRL",
        source="demo",
        dataset="demo-history",
        data_level=DataLevel.DEMO,
        freshness=Freshness.STALE,
        source_timestamp=datetime(2026, 9, 2, 12, tzinfo=UTC),
        collected_at=datetime(2026, 9, 2, 12, tzinfo=UTC),
        latency_ms=8,
        mode=SeriesMode.INDEX_100,
        points=[],
    )
    assert series.latency_ms == 8 and series.fallback_tabular


def test_provider_result_rejects_financial_float_and_adapter_raw_payload():
    with pytest.raises(ValueError):
        ProviderResult(value=1.2, provenance=_provenance())
    dataset = ProviderDatasetRef(
        provider="brapi", dataset="quotes", license_status="PUBLIC_APPROVED",
        public_approved=True, evidence=True,
    )
    adapter = BrapiAdapter(
        dataset=dataset,
        token="fixture-token",
        transport=lambda **_: ProviderHttpResponse(200, {"price": "1", "currency": "BRL", "timestamp": "2026-09-02T12:00:00Z"}),
        normalizer=lambda *_: {"price": "raw"},
    )
    with pytest.raises(Exception, match="normalized"):
        adapter.latest_quote("equity.br.b3.petr4")


def test_cache_envelope_rejects_missing_provenance():
    with pytest.raises(ValueError):
        CacheEnvelope(
            value=Decimal("10"), source="demo", dataset="demo", data_level=DataLevel.DEMO,
            freshness=Freshness.STALE, source_timestamp=None,
            collected_at=datetime.now(UTC), cached_at=datetime.now(UTC),
            fresh_until=datetime.now(UTC), stale_until=datetime.now(UTC), currency="BRL",
        )


def test_calendar_handles_b3_us_holidays_and_ttl_calendar_argument():
    b3 = WeekdayMarketCalendar("America/Sao_Paulo", holidays=frozenset({date(2026, 9, 7)}))
    nyse = WeekdayMarketCalendar("America/New_York", holidays=frozenset({date(2026, 7, 3)}))
    assert b3.is_trading_day(date(2026, 9, 4))
    assert not b3.is_trading_day(date(2026, 9, 7))
    assert not nyse.is_trading_day(date(2026, 7, 3))
    result = compute_freshness(
        DataLevel.DELAYED,
        datetime(2026, 9, 7, 12, tzinfo=UTC),
        now=datetime(2026, 9, 7, 13, tzinfo=UTC),
        calendar=b3,
    )
    assert result.reason_code == "NON_TRADING_DAY_SOURCE"
