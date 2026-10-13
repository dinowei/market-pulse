"""ADR-029: the owner's real-data universe, widened to what the plans serve, with no network.

Payloads follow the shapes the providers returned in the probes of 2026-10-13 (field names
only); every value is fictitious. Twelve Data sends no `currency` for pairs, and its daily
bars for crypto, forex and gold carry no volume.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from test_live_data_adr027 import (
    APPROVED,
    KEYS,
    FakeNet,
    _no_redis,
    brapi_quote_payload,
    http_error,
)

from app import routers
from app.contracts import HistoryPeriod, SeriesMode
from app.core.config import get_settings
from app.instruments.catalog import (
    MASTER_CATALOG,
    P0_OPERATIONAL_UNIVERSE,
    CoverageTier,
    DataSupportStatus,
)
from app.main import app
from app.market_data import live_data
from app.market_data.benchmarks import benchmark_ids
from app.market_data.normalization import AdjustmentType
from app.market_data.real_market_data import real_benchmarks, real_quote, real_series
from app.providers.canonical import NormalizationError, QualityStatus, UnavailableReason
from app.providers.models import DataLevel, ProviderCapability
from app.providers.precedence import serve
from app.providers.registry import ActivationDecision
from app.providers.resilience import CircuitBreaker
from app.providers.vendors import InstrumentRef, twelve_data_quote, twelve_data_series

NOW = datetime.now(UTC).replace(microsecond=0)
NEW_IDS = (
    "equity.br.b3.itub4",
    "equity.br.b3.wege3",
    "etf.br.b3.bova11",
    "equity.us.nasdaq.msft",
    "equity.us.nasdaq.nvda",
    "etf.us.nysearca.spy",
    "crypto.global.eth-usd",
    "fx.global.usd-brl",
    "fx.global.eur-usd",
    "commodity.global.xau-usd",
)


@pytest.fixture
def net(monkeypatch):
    monkeypatch.setenv("MARKET_PULSE_REAL_DATA_PROVIDERS", APPROVED)
    for name in KEYS:
        monkeypatch.setenv(name, f"FAKE-{name}")
    get_settings.cache_clear()
    live_data.reset_state()
    fake = FakeNet()
    monkeypatch.setattr(live_data, "OPENER", [fake])
    monkeypatch.setattr(live_data, "backoff_delay", lambda *args, **kwargs: 0)
    monkeypatch.setattr(live_data._Store, "_client", staticmethod(_no_redis))
    yield fake
    get_settings.cache_clear()
    live_data.reset_state()


def pair_quote_payload(symbol="BTC/USD", close="81553.68"):
    return {
        "symbol": symbol,
        "name": "Bitcoin US Dollar",
        "exchange": "Binance",
        "datetime": NOW.date().isoformat(),
        "timestamp": int(NOW.timestamp()) - 3600,
        "open": "81850.01",
        "high": "81959.53",
        "low": "81297.19",
        "close": close,
        "previous_close": "81850",
        "change": "-296.32000",
        "percent_change": "-0.36202810",
        "is_market_open": True,
    }


def pair_series_payload(symbol="BTC/USD", quote_name="US Dollar", closes=("100", "101", "102")):
    values = [
        {
            "datetime": (NOW - timedelta(days=len(closes) - 1 - index)).date().isoformat(),
            "open": close,
            "high": close,
            "low": close,
            "close": close,
        }
        for index, close in enumerate(closes)
    ]
    return {
        "meta": {
            "symbol": symbol,
            "interval": "1day",
            "currency_base": "Bitcoin",
            "currency_quote": quote_name,
            "type": "Digital Currency",
        },
        "values": list(reversed(values)),
        "status": "ok",
    }


# --- Catalog -----------------------------------------------------------------------------------


def test_every_live_instrument_is_named_by_the_catalog_or_the_benchmarks():
    catalog = {entry.canonical_id: entry for entry in MASTER_CATALOG}
    for canonical_id, instrument in live_data.LIVE_INSTRUMENTS.items():
        assert canonical_id in catalog or canonical_id in benchmark_ids(), canonical_id
        if canonical_id in catalog:
            assert catalog[canonical_id].currency == instrument.currency, canonical_id
    for canonical_id in NEW_IDS:
        entry = catalog[canonical_id]
        assert canonical_id not in P0_OPERATIONAL_UNIVERSE
        assert entry.coverage_tier is CoverageTier.P1
        assert entry.data_support_status is DataSupportStatus.PROVIDER_PENDING
        assert canonical_id in live_data.LIVE_INSTRUMENTS


def test_outside_the_owner_session_the_new_instruments_are_never_priced(net):
    client = TestClient(app)
    for canonical_id in NEW_IDS:
        body = client.get(f"/api/v1/market-data/quotes/{canonical_id}").json()
        assert body["unavailable_reason"] == "SESSION_REQUIRED", canonical_id
        assert body["price"] is None and body["is_demo"] is False
    assert net.calls == []


# --- Twelve Data pairs -------------------------------------------------------------------------


def test_crypto_quote_comes_from_the_pair_and_says_the_market_never_closes(net):
    net.routes["api.twelvedata.com/quote"] = pair_quote_payload()
    quote = real_quote("crypto.global.btc-usd", "req")
    assert quote.price == Decimal("81553.68") and quote.currency == "USD"
    assert quote.change == Decimal("-296.32000")
    assert quote.change_percent == Decimal("-0.36202810")
    assert quote.provider == "twelve_data" and quote.is_demo is False
    assert quote.session_date == NOW.date() and quote.timestamp_official is None
    assert quote.data_level == DataLevel.DELAYED, "never sold as real time"
    assert live_data.ROUND_THE_CLOCK_NOTE in quote.limitations


def test_pair_bars_have_no_volume_and_never_get_a_zero(net):
    net.routes["api.twelvedata.com/time_series"] = pair_series_payload("ETH/USD")
    series = real_series("crypto.global.eth-usd", HistoryPeriod.ONE_M, SeriesMode.PRICE, "req")
    assert [point.close for point in series.points] == [
        Decimal("100"),
        Decimal("101"),
        Decimal("102"),
    ]
    assert all(point.volume is None for point in series.points)
    assert series.currency == "USD" and series.provider == "twelve_data"
    assert live_data.ROUND_THE_CLOCK_NOTE in series.limitations


def test_a_pair_answer_for_another_symbol_or_currency_is_refused():
    ref = InstrumentRef("fx.global.eur-usd", "EUR/USD", "USD")
    with pytest.raises(NormalizationError):
        twelve_data_series(
            pair_series_payload("GBP/USD"), ref, adjustment=AdjustmentType.UNADJUSTED
        )
    wrong_catalog = InstrumentRef("fx.global.eur-usd", "EUR/USD", "BRL")
    quote = twelve_data_quote(
        pair_quote_payload("EUR/USD", "1.11577"),
        wrong_catalog,
        dataset="twelve_data.quote",
        data_level=DataLevel.DELAYED,
        request_id="req",
        now=NOW,
    )
    assert quote.quality_status is QualityStatus.QUARANTINED, "a currency mismatch is not served"
    with pytest.raises(NormalizationError):
        # A ticker (not a pair) still needs the currency field.
        twelve_data_quote(
            {**pair_quote_payload("AAPL", "100"), "symbol": "AAPL"},
            InstrumentRef("equity.us.nasdaq.aapl", "AAPL", "USD"),
            dataset="twelve_data.quote",
            data_level=DataLevel.DELAYED,
            request_id="req",
            now=NOW,
        )


def test_usd_brl_gets_bars_from_twelve_data_while_the_benchmark_keeps_its_source(net):
    net.routes["openexchangerates.org"] = {
        "base": "USD",
        "rates": {"BRL": "5.4321"},
        "timestamp": int(NOW.timestamp()) - 600,
    }
    net.routes["brapi.dev/api/v2/stocks/quote"] = brapi_quote_payload(symbol="^BVSP")
    net.routes["api.twelvedata.com/time_series"] = pair_series_payload(
        "USD/BRL", "Brazil Real", ("5.40", "5.42", "5.44")
    )
    net.routes["api.twelvedata.com/quote"] = pair_quote_payload("USD/BRL", "5.44")
    benchmark = {item.canonical_id: item for item in real_benchmarks()}["fx.global.usd-brl"]
    assert benchmark.source == "open_exchange_rates" and benchmark.value == Decimal("5.4321")
    series = real_series("fx.global.usd-brl", HistoryPeriod.ONE_M, SeriesMode.PRICE, "req")
    assert series.provider == "twelve_data" and series.currency == "BRL"
    assert [point.close for point in series.points][-1] == Decimal("5.44")
    quote = real_quote("fx.global.usd-brl", "req")
    assert quote.provider == "twelve_data" and quote.currency == "BRL"


def test_gold_spot_is_served_in_dollars(net):
    net.routes["api.twelvedata.com/quote"] = pair_quote_payload("XAU/USD", "4165.23022")
    quote = real_quote("commodity.global.xau-usd", "req")
    assert quote.price == Decimal("4165.23022") and quote.currency == "USD"
    assert quote.asset_type == "COMMODITY"


# --- B3 on the owner's brapi plan --------------------------------------------------------------


def test_refused_b3_history_never_blocks_brapi_quotes(net):
    net.routes["brapi.dev/api/v2/stocks/historical"] = http_error(403)
    for canonical_id in (
        "equity.br.b3.wege3",
        "equity.br.b3.itub4",
        "etf.br.b3.bova11",
        "equity.br.b3.cmin3",
    ):
        series = real_series(canonical_id, HistoryPeriod.ONE_M, SeriesMode.PRICE, "req")
        assert series.points == [] and series.unavailable_reason == "LICENSE_BLOCKED"
    net.routes["brapi.dev/api/v2/stocks/quote"] = brapi_quote_payload(price="61.20", symbol="VALE3")
    quote = real_quote("equity.br.b3.vale3", "req")
    assert quote.price == Decimal("61.20") and quote.provider == "brapi"
    asked = net.count("brapi.dev/api/v2/stocks/historical")
    real_series("equity.br.b3.wege3", HistoryPeriod.ONE_M, SeriesMode.PRICE, "req")
    assert net.count("brapi.dev/api/v2/stocks/historical") == asked, "a refusal is remembered"


def test_query_refusals_do_not_open_the_circuit():
    def allow(entry, environ=None):
        return ActivationDecision(True, None)

    def refuse(provider_id: str):
        raise NormalizationError(UnavailableReason.LICENSE_BLOCKED, "fora do plano")

    breakers = {"brapi": CircuitBreaker(failure_threshold=1, cooldown_seconds=60)}
    for _ in range(3):
        result, trace = serve(
            ProviderCapability.HISTORICAL_BARS, "BR", refuse, breakers=breakers, decide=allow
        )
        assert result is None and trace.reason is UnavailableReason.LICENSE_BLOCKED
    assert breakers["brapi"].state == CircuitBreaker.CLOSED


def test_the_owner_session_sees_crypto_through_the_api(net, monkeypatch):
    monkeypatch.setattr(routers, "_signed_in", lambda request: True)
    net.routes["api.twelvedata.com/quote"] = pair_quote_payload("ETH/USD", "2431.94")
    body = TestClient(app).get("/api/v1/market-data/quotes/crypto.global.eth-usd").json()
    assert body["price"] == "2431.94" and body["provider"] == "twelve_data"
    assert body["license_status"] == "OWNER_APPROVED_PRIVATE_STAGING"
