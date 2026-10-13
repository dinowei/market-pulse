"""ADR-027: opt-in calls to the real providers, one request per endpoint, no loops.

Skipped unless MARKET_PULSE_LIVE_PROVIDER_TESTS=1. Credentials come from the environment or
from apps/api/.env and are never printed: each line reports provider, endpoint, outcome and
reason only. A provider may legitimately refuse (plan, quota); the test then checks that the
refusal maps to a public reason instead of crashing or leaking anything.

    MARKET_PULSE_LIVE_PROVIDER_TESTS=1 uv run --frozen pytest -s tests/test_live_providers_optin.py
"""

import os
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.market_data import live_data
from app.market_data.normalization import AdjustmentType
from app.providers import vendors
from app.providers.canonical import NormalizationError, UnavailableReason
from app.providers.models import DataLevel
from app.providers.vendors import InstrumentRef

pytestmark = pytest.mark.skipif(
    os.environ.get("MARKET_PULSE_LIVE_PROVIDER_TESTS") != "1",
    reason="opt-in: set MARKET_PULSE_LIVE_PROVIDER_TESTS=1 to call the real providers",
)

KEYS = (
    "BRAPI_API_KEY",
    "TWELVE_DATA_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "OPEN_EXCHANGE_RATES_APP_ID",
    "MASSIVE_API_KEY",
)
PETR4 = InstrumentRef("equity.br.b3.petr4", "PETR4", "BRL")
IBOV = InstrumentRef("index.br.b3.ibovespa", "^BVSP", "BRL")
AAPL = InstrumentRef("equity.us.nasdaq.aapl", "AAPL", "USD")
OUTCOMES: list[str] = []


def _env_file_values() -> dict[str, str]:
    path = Path(__file__).parents[1] / ".env"
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if text and not text.startswith("#") and "=" in text:
            key, value = text.split("=", 1)
            if key.strip() in KEYS:
                values[key.strip()] = value.strip().strip("\"'")
    return values


@pytest.fixture(scope="module", autouse=True)
def live_env():
    patch = pytest.MonkeyPatch()
    for key, value in _env_file_values().items():
        if not os.environ.get(key):
            patch.setenv(key, value)
    patch.setenv("MARKET_PULSE_REAL_DATA_PROVIDERS", ",".join(live_data.PLAN_LEVEL))
    patch.setattr(live_data._Store, "_client", staticmethod(_no_redis))
    get_settings.cache_clear()
    live_data.reset_state()
    yield
    print("\n" + "\n".join(OUTCOMES))
    patch.undo()
    get_settings.cache_clear()
    live_data.reset_state()


def _no_redis():
    raise ConnectionError("the opt-in run keeps its budget in the process")


def _call(provider_id: str, endpoint: str, operation):
    if not os.environ.get(get_entry_env(provider_id)):
        OUTCOMES.append(f"{provider_id:<20} {endpoint:<24} SKIP  credencial AUSENTE")
        pytest.skip(f"{provider_id}: credential absent")
    try:
        value = operation()
    except NormalizationError as error:
        assert error.reason in UnavailableReason
        for key in KEYS:
            secret = os.environ.get(key)
            assert not secret or secret not in str(error), "an error message carried a credential"
        OUTCOMES.append(
            f"{provider_id:<20} {endpoint:<24} RECUSA {error.reason.value} HTTP {error.http_status}"
        )
        return None
    OUTCOMES.append(f"{provider_id:<20} {endpoint:<24} OK")
    return value


def get_entry_env(provider_id: str) -> str:
    from app.providers.registry import get_entry

    return get_entry(provider_id).credential_envs[0]


def _now() -> datetime:
    return datetime.now(UTC)


def test_brapi_quote_and_index():
    for ref, label in ((PETR4, "quote PETR4"), (IBOV, "quote ^BVSP")):
        quote = _call(
            "brapi",
            label,
            lambda ref=ref: vendors.brapi_quote(
                live_data._send("brapi", vendors.brapi_quote_request(ref)),
                ref,
                dataset="brapi.v2.stocks.quote",
                data_level=DataLevel.DELAYED,
                request_id="optin",
                now=_now(),
            ),
        )
        if quote is not None:
            assert quote.price > 0 and quote.currency == "BRL" and quote.source_timestamp


def test_brapi_unadjusted_history():
    series = _call(
        "brapi",
        "historical PETR4 raw",
        lambda: vendors.brapi_series(
            live_data._send("brapi", vendors.brapi_series_request(PETR4, "1mo")), PETR4
        ),
    )
    if series is not None:
        assert series.bars and all(
            bar.adjustment_type is AdjustmentType.UNADJUSTED for bar in series.bars
        )


def test_twelve_data_quote_and_series():
    quote = _call(
        "twelve_data",
        "quote AAPL",
        lambda: vendors.twelve_data_quote(
            live_data._send("twelve_data", vendors.twelve_data_quote_request(AAPL)),
            AAPL,
            dataset="twelve_data.quote",
            data_level=DataLevel.DELAYED,
            request_id="optin",
            now=_now(),
        ),
    )
    if quote is not None:
        assert quote.price > 0 and quote.currency == "USD"
    series = _call(
        "twelve_data",
        "time_series AAPL",
        lambda: vendors.twelve_data_series(
            live_data._send("twelve_data", vendors.twelve_data_series_request(AAPL, 5)),
            AAPL,
            adjustment=AdjustmentType.UNADJUSTED,
        ),
    )
    if series is not None:
        assert len(series.bars) <= 5


def test_alpha_vantage_quote():
    quote = _call(
        "alpha_vantage",
        "GLOBAL_QUOTE AAPL",
        lambda: vendors.alpha_vantage_quote(
            live_data._send("alpha_vantage", vendors.alpha_vantage_quote_request(AAPL)),
            AAPL,
            dataset="alpha_vantage.global_quote",
            request_id="optin",
            now=_now(),
        ),
    )
    if quote is not None:
        assert quote.price > 0 and quote.session_date <= date.today()


def test_open_exchange_rates_usd_brl():
    rate = _call(
        "open_exchange_rates",
        "latest USD/BRL",
        lambda: vendors.open_exchange_rates_rate(
            live_data._send("open_exchange_rates", vendors.open_exchange_rates_request()),
            base="USD",
            quote="BRL",
            dataset="open_exchange_rates.latest",
            data_level=DataLevel.DELAYED,
            request_id="optin",
            now=_now(),
        ),
    )
    if rate is not None:
        assert rate.rate > 0


def test_massive_daily_bars():
    end = _now().date()
    series = _call(
        "massive",
        "aggs AAPL 10d",
        lambda: vendors.massive_bars(
            live_data._send(
                "massive", vendors.massive_bars_request(AAPL, end - timedelta(days=10), end)
            ),
            AAPL,
        ),
    )
    if series is not None:
        assert all(bar.currency == "USD" for bar in series.bars)


# --- ADR-029: the widened universe ------------------------------------------------------------

PAIRS = (
    InstrumentRef("crypto.global.eth-usd", "ETH/USD", "USD"),
    InstrumentRef("fx.global.usd-brl", "USD/BRL", "BRL"),
    InstrumentRef("fx.global.eur-usd", "EUR/USD", "USD"),
    InstrumentRef("commodity.global.xau-usd", "XAU/USD", "USD"),
)
B3 = ("VALE3", "ITUB4", "WEGE3", "CMIN3", "BOVA11", "MXRF11", "AAPL34")


def test_twelve_data_pairs_adr029():
    # Basic plan: 8 credits per minute, and the AAPL test above spent 2 of them.
    time.sleep(61)
    for ref in (
        InstrumentRef("crypto.global.btc-usd", "BTC/USD", "USD"),
        InstrumentRef("fx.global.usd-brl", "USD/BRL", "BRL"),
        InstrumentRef("equity.us.nasdaq.nvda", "NVDA", "USD"),
    ):
        quote = _call(
            "twelve_data",
            f"quote {ref.provider_symbol}",
            lambda ref=ref: vendors.twelve_data_quote(
                live_data._send("twelve_data", vendors.twelve_data_quote_request(ref)),
                ref,
                dataset="twelve_data.quote",
                data_level=DataLevel.DELAYED,
                request_id="optin",
                now=_now(),
            ),
        )
        if quote is not None:
            assert quote.price > 0 and quote.currency == ref.currency
    for ref in PAIRS:
        series = _call(
            "twelve_data",
            f"time_series {ref.provider_symbol}",
            lambda ref=ref: vendors.twelve_data_series(
                live_data._send("twelve_data", vendors.twelve_data_series_request(ref, 5)),
                ref,
                adjustment=AdjustmentType.UNADJUSTED,
            ),
        )
        if series is not None:
            assert series.bars and all(bar.currency == ref.currency for bar in series.bars)


def test_brapi_b3_universe_adr029():
    for symbol in B3:
        ref = InstrumentRef(f"b3.{symbol.lower()}", symbol, "BRL")
        quote = _call(
            "brapi",
            f"quote {symbol}",
            lambda ref=ref: vendors.brapi_quote(
                live_data._send("brapi", vendors.brapi_quote_request(ref)),
                ref,
                dataset="brapi.v2.stocks.quote",
                data_level=DataLevel.DELAYED,
                request_id="optin",
                now=_now(),
            ),
        )
        if quote is not None:
            assert quote.price > 0 and quote.currency == "BRL"
    # Records which tickers the plan serves history for; a 403 is a valid answer here.
    for symbol in B3:
        ref = InstrumentRef(f"b3.{symbol.lower()}", symbol, "BRL")
        _call(
            "brapi",
            f"historical {symbol} raw",
            lambda ref=ref: vendors.brapi_series(
                live_data._send("brapi", vendors.brapi_series_request(ref, "1mo")), ref
            ),
        )
