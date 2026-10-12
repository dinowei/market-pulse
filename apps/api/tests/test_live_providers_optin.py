"""ADR-027: opt-in calls to the real providers, one request per endpoint, no loops.

Skipped unless MARKET_PULSE_LIVE_PROVIDER_TESTS=1. Credentials come from the environment or
from apps/api/.env and are never printed: each line reports provider, endpoint, outcome and
reason only. A provider may legitimately refuse (plan, quota); the test then checks that the
refusal maps to a public reason instead of crashing or leaking anything.

    MARKET_PULSE_LIVE_PROVIDER_TESTS=1 uv run --frozen pytest -s tests/test_live_providers_optin.py
"""

import os
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
