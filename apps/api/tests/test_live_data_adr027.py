"""ADR-027: real data for the owner's private staging, with no network in the suite.

Payloads follow each provider's documented field names; symbols are real tickers but every
value is fictitious. The fake opener records every URL, so a test can prove that a blocked
provider was never called.
"""

import io
import json
import urllib.error
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import routers
from app.contracts import HistoryPeriod, SeriesMode
from app.core.config import (
    ProductionConfigurationError,
    Settings,
    get_settings,
    validate_real_data_settings,
)
from app.main import app
from app.market_data import live_data
from app.market_data.real_market_data import (
    real_benchmarks,
    real_price_marks,
    real_price_marks_on,
    real_quote,
    real_series,
)
from app.providers.registry import CredentialStatus, credential_status, get_entry

APPROVED = "brapi,twelve_data,alpha_vantage,open_exchange_rates,massive"
KEYS = (
    "BRAPI_API_KEY",
    "TWELVE_DATA_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "OPEN_EXCHANGE_RATES_APP_ID",
    "MASSIVE_API_KEY",
)
NOW = datetime.now(UTC).replace(microsecond=0)


class _Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def ok(payload) -> _Response:
    return _Response(json.dumps(payload).encode())


def http_error(status: int, retry_after: str | None = None):
    def handler(request):
        headers = {"Retry-After": retry_after} if retry_after else {}
        raise urllib.error.HTTPError(request.full_url, status, "err", headers, io.BytesIO(b"{}"))

    return handler


class FakeNet:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.routes: dict[str, object] = {}

    def __call__(self, request, timeout):
        url = request.full_url
        self.calls.append(url)
        for fragment, handler in self.routes.items():
            if fragment in url:
                return handler(request) if callable(handler) else ok(handler)
        raise AssertionError(f"unexpected provider call: {url}")

    def count(self, fragment: str) -> int:
        return sum(fragment in url for url in self.calls)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None):
        self.values[key] = value

    def incr(self, key):
        self.values[key] = str(int(self.values.get(key, "0")) + 1)
        return int(self.values[key])

    def expire(self, key, ttl):
        return True


def _no_redis():
    raise ConnectionError("redis down in the test")


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


def brapi_quote_payload(currency="BRL", price="10.25", symbol="PETR4"):
    return {
        "results": [
            {
                "requestedSymbol": symbol,
                "symbol": symbol,
                "changed": False,
                "data": {
                    "currency": currency,
                    "regularMarketPrice": price,
                    "regularMarketChange": "-0.15",
                    "regularMarketChangePercent": "-1.44",
                    "regularMarketVolume": 1000,
                    "regularMarketTime": (NOW - timedelta(minutes=40)).isoformat(),
                },
            }
        ]
    }


def twelve_quote_payload():
    return {
        "symbol": "AAPL",
        "currency": "USD",
        "datetime": (NOW - timedelta(days=1)).date().isoformat(),
        "close": "100.50",
        "previous_close": "99.50",
        "change": "1.00",
        "percent_change": "1.00502",
        "volume": "1000",
    }


def massive_payload(closes=("98.00", "99.00", "100.00")):
    days = len(closes)
    return {
        "adjusted": False,
        "results": [
            {
                "t": int((NOW - timedelta(days=days - index)).timestamp() * 1000),
                "o": close,
                "h": close,
                "l": close,
                "c": close,
                "v": 500,
            }
            for index, close in enumerate(closes)
        ],
    }


def twelve_series_payload():
    values = []
    for index, close in enumerate(("97.00", "98.00", "99.00")):
        day = (NOW - timedelta(days=3 - index)).date().isoformat()
        values.append(
            {
                "datetime": day,
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume": "10",
            }
        )
    return {"meta": {"symbol": "AAPL", "currency": "USD"}, "values": values}


def brapi_series_payload(raw=True):
    rows = []
    for index, (close, adjusted) in enumerate((("40.00", "38.00"), ("41.00", "39.00"))):
        row = {
            "date": int((NOW - timedelta(days=2 - index)).timestamp()),
            "open": adjusted,
            "high": adjusted,
            "low": adjusted,
            "close": adjusted,
            "volume": 100,
            "adjustedClose": adjusted,
        }
        if raw:
            row |= {"rawOpen": close, "rawHigh": close, "rawLow": close, "rawClose": close}
        rows.append(row)
    return {
        "results": [
            {
                "requestedSymbol": "PETR4",
                "symbol": "PETR4",
                "changed": False,
                "data": {"usedInterval": "1d", "usedRange": "1y", "historicalDataPrice": rows},
            }
        ]
    }


# --- Configuration -----------------------------------------------------------------------------


def _settings(**values) -> Settings:
    return Settings(_env_file=None, **{"demo_enabled": False, **values})


def test_real_data_is_refused_in_production_with_demo_with_open_signup_and_for_blocked_ids():
    staging = {"environment": "staging", "registration_enabled": False}
    validate_real_data_settings(_settings(real_data_providers=APPROVED, **staging))
    with pytest.raises(ProductionConfigurationError, match="production"):
        validate_real_data_settings(
            _settings(real_data_providers="brapi", environment="production")
        )
    with pytest.raises(ProductionConfigurationError, match="never mix"):
        validate_real_data_settings(
            _settings(real_data_providers="brapi", demo_enabled=True, **staging)
        )
    with pytest.raises(ProductionConfigurationError, match="registration"):
        validate_real_data_settings(_settings(real_data_providers="brapi", environment="local"))
    with pytest.raises(ProductionConfigurationError, match="b3_developers"):
        validate_real_data_settings(_settings(real_data_providers="brapi,b3_developers", **staging))
    with pytest.raises(ProductionConfigurationError, match="hg"):
        validate_real_data_settings(_settings(real_data_providers="hg", **staging))
    assert _settings(real_data_providers=" Brapi , twelve_data,brapi ").real_data_providers == (
        "brapi",
        "twelve_data",
    )
    assert _settings().real_data_providers == ()


def test_credential_status_shows_names_only():
    entry = get_entry("brapi")
    environ = {"BRAPI_API_KEY": "FAKE-VALUE-123", "BRAPI_API_TOKEN": "FAKE-VALUE-456"}
    status = credential_status(entry, environ)
    assert status == {
        "BRAPI_API_KEY": CredentialStatus.PRESENT,
        "BRAPI_API_TOKEN": CredentialStatus.NOT_READ,
    }
    assert credential_status(entry, {}) == {"BRAPI_API_KEY": CredentialStatus.MISSING}
    assert (
        credential_status(entry, environ, rejected=True)["BRAPI_API_KEY"]
        is CredentialStatus.INVALID
    )
    assert "FAKE-VALUE" not in repr(status)


# --- Quotes ------------------------------------------------------------------------------------


def test_brazilian_quote_is_real_fresh_and_cached(net):
    net.routes["brapi.dev/api/v2/stocks/quote"] = brapi_quote_payload()
    quote = real_quote("equity.br.b3.petr4", "req-1")
    assert (quote.provider, quote.data_level, quote.freshness) == ("brapi", "DELAYED", "FRESH")
    assert quote.price == Decimal("10.25") and quote.change == Decimal("-0.15")
    assert quote.is_demo is False and quote.fallback_used is False
    assert quote.license_status == "OWNER_APPROVED_PRIVATE_STAGING"
    assert quote.timezone == "America/Sao_Paulo" and quote.observed_at is not None
    assert quote.timestamp_official < quote.timestamp_collected and quote.latency_ms > 0
    assert any("ADR-027" in note for note in quote.limitations)
    real_quote("equity.br.b3.petr4", "req-2")
    assert net.count("brapi.dev") == 1, "the second request is served from the cache"


def test_redis_holds_the_cache_and_the_budget(net, monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(live_data._Store, "_client", staticmethod(lambda: redis))
    net.routes["brapi.dev/api/v2/stocks/quote"] = brapi_quote_payload()
    real_quote("equity.br.b3.petr4", "req-1")
    assert any(key.startswith("market_data:live:quote:") for key in redis.values)
    assert any(":budget:brapi:day:" in key for key in redis.values)
    assert not any("FAKE-" in value for value in redis.values.values()), "no credential cached"


def test_us_quote_falls_back_and_respects_retry_after(net):
    net.routes["api.twelvedata.com/quote"] = http_error(429, retry_after="30")
    net.routes["api.massive.com"] = massive_payload()
    quote = real_quote("equity.us.nasdaq.aapl", "req-1")
    assert (quote.provider, quote.fallback_used, quote.data_level) == ("massive", True, "EOD")
    assert quote.price == Decimal("100.00") and quote.change == Decimal("1.00")
    assert any("Fonte reserva" in note for note in quote.limitations)
    assert net.count("twelvedata") == 1, "429 is never retried"
    assert live_data.STORE.get(live_data._key("cooldown", "twelve_data")) == "RATE_LIMITED"


def test_session_only_source_keeps_the_trading_day_without_inventing_a_time(net):
    net.routes["api.twelvedata.com/quote"] = twelve_quote_payload()
    quote = real_quote("equity.us.nasdaq.aapl", "req-1")
    assert quote.provider == "twelve_data" and quote.timestamp_official is None
    assert quote.session_date == (NOW - timedelta(days=1)).date() and quote.latency_ms is None


def test_401_marks_the_key_invalid_and_is_not_retried(net):
    net.routes["api.twelvedata.com/quote"] = http_error(401)
    net.routes["api.massive.com"] = http_error(403)
    net.routes["alphavantage.co"] = {"Information": "limit"}
    quote = real_quote("equity.us.nasdaq.aapl", "req-1")
    assert quote.freshness == "UNAVAILABLE" and quote.price is None and quote.change is None
    assert net.count("twelvedata") == 1 and net.count("massive") == 1
    assert live_data.credential_rejected("twelve_data")
    status = credential_status(get_entry("twelve_data"), rejected=True)
    assert status["TWELVE_DATA_API_KEY"] is CredentialStatus.INVALID


def test_timeout_and_5xx_retry_once_then_answer_unavailable_never_zero(net):
    def timeout(request):
        raise TimeoutError

    net.routes["brapi.dev"] = timeout
    quote = real_quote("equity.br.b3.petr4", "req-1")
    assert net.count("brapi.dev") == 2, "one retry, then stop"
    assert quote.freshness == "UNAVAILABLE" and quote.unavailable_reason == "SOURCE_ERROR"
    assert quote.price is None and quote.change_percent is None and quote.is_demo is False
    live_data.reset_state()
    net.calls.clear()
    net.routes["brapi.dev"] = http_error(503)
    assert real_quote("equity.br.b3.petr4", "req-2").unavailable_reason == "SOURCE_ERROR"
    assert net.count("brapi.dev") == 2


def test_404_empty_and_currency_mismatch_are_never_served(net):
    net.routes["brapi.dev"] = http_error(404)
    assert real_quote("equity.br.b3.petr4", "r").unavailable_reason == "SOURCE_ERROR"
    live_data.reset_state()
    net.routes["brapi.dev"] = {"results": []}
    assert real_quote("equity.br.b3.petr4", "r").unavailable_reason == "SCHEMA_UNSUPPORTED"
    live_data.reset_state()
    net.routes["brapi.dev"] = brapi_quote_payload(currency="USD")
    quote = real_quote("equity.br.b3.petr4", "r")
    assert quote.unavailable_reason == "SCHEMA_UNSUPPORTED" and quote.price is None


def test_failed_refresh_serves_the_last_validated_value_as_stale(net, monkeypatch):
    net.routes["brapi.dev"] = brapi_quote_payload()
    real_quote("equity.br.b3.petr4", "r")
    later = datetime.now(UTC) + timedelta(hours=2)
    monkeypatch.setattr(live_data, "_now", lambda: later)
    net.routes["brapi.dev"] = http_error(500)
    quote = real_quote("equity.br.b3.petr4", "r")
    assert quote.freshness == "STALE" and quote.price == Decimal("10.25")
    assert quote.unavailable_reason == "SOURCE_ERROR"
    assert any("Último valor validado" in note for note in quote.limitations)


def test_unapproved_or_unconfigured_providers_are_never_called(net, monkeypatch):
    monkeypatch.setenv("MARKET_PULSE_REAL_DATA_PROVIDERS", "twelve_data")
    get_settings.cache_clear()
    assert real_quote("equity.br.b3.petr4", "r").unavailable_reason == "DATASET_NOT_APPROVED"
    monkeypatch.setenv("MARKET_PULSE_REAL_DATA_PROVIDERS", APPROVED)
    monkeypatch.delenv("BRAPI_API_KEY")
    get_settings.cache_clear()
    live_data.reset_state()
    assert real_quote("equity.br.b3.petr4", "r").unavailable_reason == "PROVIDER_NOT_CONFIGURED"
    assert net.calls == []


def test_a_403_refuses_that_query_only_and_is_not_asked_again(net):
    # Measured on 2026-10-12: brapi answers 403 to the index history outside the plan.
    net.routes["brapi.dev/api/v2/stocks/historical"] = http_error(403)
    net.routes["brapi.dev/api/v2/stocks/quote"] = brapi_quote_payload(symbol="^BVSP")
    first = real_series("index.br.b3.ibovespa", HistoryPeriod.ONE_M, SeriesMode.PRICE, "r")
    again = real_series("index.br.b3.ibovespa", HistoryPeriod.ONE_M, SeriesMode.PRICE, "r")
    assert first.unavailable_reason == again.unavailable_reason == "LICENSE_BLOCKED"
    assert net.count("historical") == 1, "the refused query is remembered"
    items = {item.canonical_id: item for item in real_benchmarks()}
    assert items["index.br.b3.ibovespa"].source == "brapi", "the provider still serves quotes"


def test_the_daily_budget_stops_calls_before_the_plan_limit(net, monkeypatch):
    monkeypatch.setitem(live_data.BUDGETS, "brapi", (None, 1))
    net.routes["brapi.dev"] = brapi_quote_payload()
    real_quote("equity.br.b3.petr4", "r")
    live_data.STORE._memory = {
        key: value for key, value in live_data.STORE._memory.items() if ":quote:" not in key
    }
    assert real_quote("equity.br.b3.petr4", "r").unavailable_reason == "RATE_LIMITED"
    assert net.count("brapi.dev") == 1


# --- Series, FX and benchmarks -----------------------------------------------------------------


def test_us_series_is_unadjusted_and_session_dated(net):
    net.routes["api.twelvedata.com/time_series"] = twelve_series_payload()
    series = real_series("equity.us.nasdaq.aapl", HistoryPeriod.ONE_M, SeriesMode.PRICE, "r")
    assert series.provider == "twelve_data" and series.adjustment_type == "UNADJUSTED"
    assert "adjust=none" in net.calls[0]
    assert series.timestamp_official is None and series.session_date is not None
    assert [point.close for point in series.points] == [
        Decimal("97.00"),
        Decimal("98.00"),
        Decimal("99.00"),
    ]
    assert series.points[0].index_100 == Decimal("100")
    adjusted = real_series(
        "equity.us.nasdaq.aapl", HistoryPeriod.ONE_M, SeriesMode.PRICE, "r", "ADJUSTED_TOTAL_RETURN"
    )
    assert adjusted.freshness == "UNAVAILABLE" and adjusted.points == []


def test_brapi_series_uses_raw_prices_or_refuses(net):
    net.routes["brapi.dev/api/v2/stocks/historical"] = brapi_series_payload(raw=True)
    series = real_series("equity.br.b3.petr4", HistoryPeriod.ONE_M, SeriesMode.PRICE, "r")
    assert [point.close for point in series.points] == [Decimal("40.00"), Decimal("41.00")]
    assert "includeRaw=true" in net.calls[0]
    live_data.reset_state()
    net.routes["brapi.dev/api/v2/stocks/historical"] = brapi_series_payload(raw=False)
    refused = real_series("equity.br.b3.petr4", HistoryPeriod.ONE_M, SeriesMode.PRICE, "r")
    assert refused.unavailable_reason == "SCHEMA_UNSUPPORTED" and refused.points == []


def test_benchmarks_are_real_or_unavailable_never_demo(net):
    net.routes["openexchangerates.org"] = {
        "base": "USD",
        "rates": {"BRL": "5.4321"},
        "timestamp": int(NOW.timestamp()) - 600,
    }
    net.routes["brapi.dev/api/v2/stocks/quote"] = brapi_quote_payload(
        price="120000.50", symbol="^BVSP"
    )
    items = {item.canonical_id: item for item in real_benchmarks()}
    assert items["fx.global.usd-brl"].value == Decimal("5.4321")
    assert items["fx.global.usd-brl"].source == "open_exchange_rates"
    assert items["index.br.b3.ibovespa"].value == Decimal("120000.50")
    assert items["rate.br.cdi"].freshness == "UNAVAILABLE" and items["rate.br.cdi"].value is None
    assert all(item.is_demo is False and item.data_level != "DEMO" for item in items.values())


def test_portfolio_marks_are_real_and_past_days_use_that_session(net):
    net.routes["api.twelvedata.com/quote"] = twelve_quote_payload()
    net.routes["openexchangerates.org"] = {
        "base": "USD",
        "rates": {"BRL": "5.40"},
        "timestamp": int(NOW.timestamp()),
    }
    prices, fx = real_price_marks(["equity.us.nasdaq.aapl", "equity.br.b3.unknown"])
    assert prices["equity.us.nasdaq.aapl"].value == Decimal("100.50")
    assert "equity.br.b3.unknown" not in prices, "missing stays missing, never a synthetic mark"
    assert fx[("USD", "BRL")].rate == Decimal("5.40")
    net.routes["api.twelvedata.com/time_series"] = twelve_series_payload()
    two_days_ago = (NOW - timedelta(days=2)).date()
    marks = real_price_marks_on(["equity.us.nasdaq.aapl"], two_days_ago)
    assert marks["equity.us.nasdaq.aapl"].value == Decimal("98.00")


# --- HTTP: who sees what -----------------------------------------------------------------------


def test_anonymous_visitors_get_session_required_and_no_provider_call(net):
    client = TestClient(app)
    response = client.get("/api/v1/market-data/quotes/equity.br.b3.petr4")
    body = response.json()
    assert response.status_code == 200 and body["unavailable_reason"] == "SESSION_REQUIRED"
    assert body["is_demo"] is False and body["data_level"] != "DEMO" and body["price"] is None
    assert response.headers["cache-control"] == "private, no-store"
    benchmarks = client.get("/api/v1/market-data/benchmarks").json()["items"]
    assert {item["unavailable_reason"] for item in benchmarks} == {"SESSION_REQUIRED"}
    assert net.calls == []


def test_the_owner_session_gets_real_data_without_shared_caching(net, monkeypatch):
    monkeypatch.setattr(routers, "_signed_in", lambda request: True)
    net.routes["brapi.dev/api/v2/stocks/quote"] = brapi_quote_payload()
    client = TestClient(app)
    response = client.get("/api/v1/market-data/quotes/equity.br.b3.petr4")
    assert response.json()["provider"] == "brapi" and response.json()["is_demo"] is False
    assert response.headers["cache-control"] == "private, no-store"
    tiles = client.get("/api/v1/market-data/heatmap").json()["groups"][0]["tiles"]
    assert {tile["provider"] for tile in tiles if tile["canonical_id"] == "equity.br.b3.petr4"} == {
        "brapi"
    }
    assert all(tile["data_level"] != "DEMO" for tile in tiles), (
        "DEMO and real never share a response"
    )


def test_a_protected_environment_without_providers_never_falls_back_to_demo(monkeypatch):
    monkeypatch.delenv("MARKET_PULSE_REAL_DATA_PROVIDERS", raising=False)
    monkeypatch.setenv("MARKET_PULSE_ENVIRONMENT", "staging")
    get_settings.cache_clear()
    try:
        client = TestClient(app)
        body = client.get("/api/v1/market-data/quotes/equity.br.b3.petr4").json()
        assert body["unavailable_reason"] == "PROVIDER_NOT_CONFIGURED" and body["is_demo"] is False
        series = client.get(
            "/api/v1/market-data/history/index.br.b3.ibovespa", params={"period": "1M"}
        ).json()
        assert series["unavailable_reason"] == "PROVIDER_NOT_CONFIGURED" and series["points"] == []
    finally:
        get_settings.cache_clear()


def test_local_synthetic_mode_is_unchanged_and_says_it_is_demo(monkeypatch):
    monkeypatch.delenv("MARKET_PULSE_REAL_DATA_PROVIDERS", raising=False)
    get_settings.cache_clear()
    body = TestClient(app).get("/api/v1/market-data/quotes/equity.br.b3.petr4").json()
    assert body["data_level"] == "DEMO" and body["is_demo"] is True
