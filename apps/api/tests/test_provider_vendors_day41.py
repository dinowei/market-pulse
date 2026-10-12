"""ADR-025: vendor normalizers, HTTP transport and series quality.

Fixtures are synthetic: field names follow each provider's official documentation (checked on
2026-10-11); symbols and values are fictitious and never real market data.
"""

import io
import json
import urllib.error
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.market_data.normalization import AdjustmentType, MarketBar
from app.market_data.quality import check_series, compare_sources
from app.providers.canonical import NormalizationError, QualityStatus, UnavailableReason
from app.providers.http import ProviderHttpTransport, redact_url
from app.providers.models import DataLevel
from app.providers.registry import ProviderStatus, get_entry
from app.providers.vendors import (
    InstrumentRef,
    alpha_vantage_quote,
    alpha_vantage_quote_request,
    brapi_quote,
    brapi_quote_request,
    massive_bars,
    massive_bars_request,
    open_exchange_rates_rate,
    reason_for_status,
    twelve_data_quote,
    twelve_data_series,
)

NOW = datetime(2026, 10, 11, 15, 0, tzinfo=timezone.utc)
BR = InstrumentRef("equity.br.b3.test4", "TEST4", "BRL")
US = InstrumentRef("equity.us.test.tst", "TST", "USD")
KW = {"dataset": "synthetic-test", "request_id": "req-1", "now": NOW}


def brapi_payload(**data) -> dict:
    return {
        "results": [
            {
                "requestedSymbol": "TEST4",
                "symbol": "TEST4",
                "changed": False,
                "data": {
                    "shortName": "Teste PN",
                    "currency": "BRL",
                    "regularMarketPrice": "10.25",
                    "regularMarketChange": "-0.15",
                    "regularMarketChangePercent": "-1.44",
                    "regularMarketVolume": "1000",
                    "regularMarketTime": "2026-10-11T14:30:00Z",
                    **data,
                },
            }
        ],
        "requestedAt": "2026-10-11T14:31:00Z",
        "took": 12,
    }


def test_brapi_quote_is_canonical_and_keeps_decimals() -> None:
    quote = brapi_quote(brapi_payload(), BR, data_level=DataLevel.DELAYED, **KW)
    assert quote.price == Decimal("10.25") and quote.change == Decimal("-0.15")
    assert quote.source_timestamp == datetime(2026, 10, 11, 14, 30, tzinfo=timezone.utc)
    assert (quote.data_level, quote.is_demo, quote.quality_status) == (
        DataLevel.DELAYED,
        False,
        QualityStatus.VALID,
    )
    request = brapi_quote_request(BR)
    assert request.params == {"symbols": "TEST4"} and request.auth_header == "Authorization"
    assert "token" not in json.dumps(request.params).lower()


def test_brapi_renamed_ticker_and_currency_mismatch_are_quarantined() -> None:
    payload = brapi_payload(currency="USD")
    payload["results"][0]["changed"] = True
    payload["results"][0]["symbol"] = "NEW4"
    quote = brapi_quote(payload, BR, data_level=DataLevel.DELAYED, **KW)
    assert quote.quality_status is QualityStatus.QUARANTINED
    assert any(note.startswith("TICKER_RENAMED") for note in quote.quality_notes)
    assert any(note.startswith("CURRENCY_MISMATCH") for note in quote.quality_notes)


@pytest.mark.parametrize(
    "change",
    [
        {"regularMarketPrice": None},
        {"regularMarketTime": "2026-10-11 14:30"},
        {"regularMarketTime": "2026-10-11T14:30:00"},
        {"currency": "real"},
    ],
)
def test_brapi_missing_or_ambiguous_fields_are_schema_unsupported(change: dict) -> None:
    with pytest.raises(NormalizationError) as error:
        brapi_quote(brapi_payload(**change), BR, data_level=DataLevel.DELAYED, **KW)
    assert error.value.reason is UnavailableReason.SCHEMA_UNSUPPORTED


def test_future_timestamp_and_float_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="future"):
        brapi_quote(
            brapi_payload(regularMarketTime="2026-10-12T00:00:00Z"),
            BR,
            data_level=DataLevel.DELAYED,
            **KW,
        )
    with pytest.raises(NormalizationError, match="float"):
        brapi_quote(brapi_payload(regularMarketPrice=10.25), BR, data_level=DataLevel.DELAYED, **KW)


def test_twelve_data_quote_session_date_and_error_body() -> None:
    payload = {
        "symbol": "TST",
        "currency": "USD",
        "datetime": "2026-10-10",
        "close": "50.10",
        "previous_close": "49.90",
        "change": "0.20",
        "percent_change": "0.40080",
        "volume": "2000",
    }
    quote = twelve_data_quote(payload, US, data_level=DataLevel.EOD, **KW)
    assert quote.source_timestamp is None and quote.session_date == date(2026, 10, 10)
    with pytest.raises(NormalizationError) as error:
        twelve_data_quote(
            {"code": 429, "message": "API request limit reached", "status": "error"},
            US,
            data_level=DataLevel.EOD,
            **KW,
        )
    assert error.value.reason is UnavailableReason.RATE_LIMITED and error.value.retryable


def test_twelve_data_series_sorts_and_keeps_missing_volume_absent() -> None:
    payload = {
        "meta": {"symbol": "TST", "currency": "USD", "exchange_timezone": "America/New_York"},
        "values": [
            {"datetime": "2026-10-10", "open": "2", "high": "3", "low": "1", "close": "2.5"},
            {
                "datetime": "2026-10-09",
                "open": "2",
                "high": "2",
                "low": "2",
                "close": "2",
                "volume": "5",
            },
        ],
    }
    result = twelve_data_series(payload, US, adjustment=AdjustmentType.UNADJUSTED)
    assert [bar.timestamp.day for bar in result.bars] == [9, 10]
    assert result.bars[1].volume is None, "absent volume is not zero"
    bad = json.loads(json.dumps(payload))
    bad["values"][0]["high"] = "0.5"
    with pytest.raises(NormalizationError, match="barra inválida"):
        twelve_data_series(bad, US, adjustment=AdjustmentType.UNADJUSTED)


def test_alpha_vantage_global_quote_is_eod_with_catalog_currency() -> None:
    payload = {
        "Global Quote": {
            "01. symbol": "TST",
            "02. open": "50.00",
            "03. high": "51.00",
            "04. low": "49.50",
            "05. price": "50.75",
            "06. volume": "3000",
            "07. latest trading day": "2026-10-10",
            "08. previous close": "50.00",
            "09. change": "0.75",
            "10. change percent": "1.5000%",
        }
    }
    quote = alpha_vantage_quote(payload, US, **KW)
    assert (quote.data_level, quote.currency, quote.change_percent) == (
        DataLevel.EOD,
        "USD",
        Decimal("1.5000"),
    )
    assert quote.source_timestamp is None, "no time is invented for an end-of-day source"
    assert "CURRENCY_FROM_CATALOG" in quote.quality_notes
    assert alpha_vantage_quote_request(US).auth_query_param == "apikey"
    with pytest.raises(NormalizationError) as error:
        alpha_vantage_quote({"Information": "texto livre"}, US, **KW)
    assert error.value.reason is UnavailableReason.SCHEMA_UNSUPPORTED


def test_open_exchange_rates_rate_and_documented_errors() -> None:
    payload = {"timestamp": 1791727200, "base": "USD", "rates": {"BRL": "5.1234"}}
    rate = open_exchange_rates_rate(
        payload, base="USD", quote="BRL", data_level=DataLevel.DELAYED, **KW
    )
    assert rate.rate == Decimal("5.1234") and rate.source_timestamp.tzinfo is timezone.utc
    for status, reason in (
        (401, UnavailableReason.PROVIDER_NOT_CONFIGURED),
        (429, UnavailableReason.LICENSE_BLOCKED),  # not_allowed: permission, not a rate limit
        (400, UnavailableReason.SCHEMA_UNSUPPORTED),
    ):
        with pytest.raises(NormalizationError) as error:
            open_exchange_rates_rate(
                {"error": True, "status": status, "message": "x", "description": "y"},
                base="USD",
                quote="BRL",
                data_level=DataLevel.DELAYED,
                **KW,
            )
        assert error.value.reason is reason
    with pytest.raises(NormalizationError, match="base"):
        open_exchange_rates_rate(
            {**payload, "base": "EUR"}, base="USD", quote="BRL", data_level=DataLevel.DELAYED, **KW
        )


def test_massive_bars_require_unadjusted_millisecond_series() -> None:
    payload = {
        "ticker": "TST",
        "adjusted": False,
        "status": "OK",
        "results": [
            {"o": "10", "h": "11", "l": "9", "c": "10.5", "v": "100", "t": 1791676800000},
        ],
        "next_url": "https://api.massive.com/next?cursor=abc",
    }
    result = massive_bars(payload, US)
    assert result.bars[0].timestamp == datetime(2026, 10, 11, 0, 0, tzinfo=timezone.utc)
    assert result.partial and result.notes
    with pytest.raises(NormalizationError, match="ajustada"):
        massive_bars({**payload, "adjusted": True}, US)
    request = massive_bars_request(US, date(2026, 10, 1), date(2026, 10, 10))
    assert request.params["adjusted"] == "false"


def test_reason_for_status_follows_each_provider() -> None:
    assert reason_for_status("brapi", 403) is UnavailableReason.LICENSE_BLOCKED
    assert reason_for_status("twelve_data", 401) is UnavailableReason.PROVIDER_NOT_CONFIGURED
    assert reason_for_status("massive", 429) is UnavailableReason.RATE_LIMITED
    assert reason_for_status("massive", 503) is UnavailableReason.SOURCE_ERROR


class _FakeResponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_transport_refuses_inactive_providers_before_any_network_call() -> None:
    called = []
    transport = ProviderHttpTransport(
        get_entry("brapi"), {"BRAPI_API_KEY": "x"}, opener=lambda *a, **k: called.append(a)
    )
    with pytest.raises(NormalizationError) as error:
        transport.send(brapi_quote_request(BR))
    assert error.value.reason is UnavailableReason.DATASET_NOT_APPROVED and called == []


def _active(provider_id: str):
    entry = get_entry(provider_id)
    return replace(entry, status=ProviderStatus.ACTIVE, license_status="PUBLIC_APPROVED")


def test_transport_injects_the_credential_and_parses_decimals() -> None:
    seen = {}

    def opener(request, timeout):
        seen["url"], seen["auth"] = request.full_url, request.get_header("Authorization")
        return _FakeResponse(b'{"price": 10.25}')

    transport = ProviderHttpTransport(_active("brapi"), {"BRAPI_API_KEY": "tok"}, opener=opener)
    response = transport.send(brapi_quote_request(BR))
    assert response.payload == {"price": Decimal("10.25")}
    assert seen["auth"] == "Bearer tok" and "tok" not in seen["url"]


def test_transport_maps_429_with_retry_after_and_never_leaks_the_key() -> None:
    def opener(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url, 429, "Too Many", {"Retry-After": "7"}, io.BytesIO(b"{}")
        )

    environ = {"ALPHA_VANTAGE_API_KEY": "FAKE-KEY-0001"}
    transport = ProviderHttpTransport(
        _active("alpha_vantage"), environ, opener=opener, now=lambda: NOW
    )
    with pytest.raises(NormalizationError) as error:
        transport.send(alpha_vantage_quote_request(US))
    assert error.value.reason is UnavailableReason.RATE_LIMITED and "7s" in str(error.value)
    assert "FAKE-KEY-0001" not in str(error.value)

    def unreachable(request, timeout):
        raise urllib.error.URLError("dns")

    transport = ProviderHttpTransport(_active("alpha_vantage"), environ, opener=unreachable)
    with pytest.raises(NormalizationError) as error:
        transport.send(alpha_vantage_quote_request(US))
    assert "FAKE-KEY-0001" not in str(error.value) and "REDACTED" in str(error.value)
    redacted = redact_url("https://x.test/q?symbol=TST&apikey=secret&app_id=id2")
    assert "secret" not in redacted and "id2" not in redacted and "symbol=TST" in redacted


def test_transport_timeout_is_a_retryable_source_error() -> None:
    def opener(request, timeout):
        raise TimeoutError

    transport = ProviderHttpTransport(_active("massive"), {"MASSIVE_API_KEY": "k"}, opener=opener)
    with pytest.raises(NormalizationError) as error:
        transport.send(massive_bars_request(US, date(2026, 10, 1), date(2026, 10, 2)))
    assert error.value.reason is UnavailableReason.SOURCE_ERROR and error.value.retryable


def _bar(day: int, **overrides) -> MarketBar:
    payload = {
        "canonical_id": "equity.us.test.tst",
        "currency": "USD",
        "adjustment_type": "UNADJUSTED",
        "timestamp": f"2026-10-{day:02d}T00:00:00+00:00",
        "open": "10",
        "high": "11",
        "low": "9",
        "close": "10",
        **overrides,
    }
    return MarketBar.from_payload(payload)


def test_series_quality_flags_duplicates_order_future_and_mixtures() -> None:
    assert check_series([_bar(8), _bar(9)], now=NOW).status is QualityStatus.VALID
    issues = check_series(
        [
            _bar(9),
            _bar(8),
            _bar(8),
            _bar(20),
            _bar(7, currency="BRL"),
            _bar(6, adjustment_type="ADJUSTED_SPLIT_ONLY"),
        ],
        now=NOW,
    )
    codes = {issue.code for issue in issues.issues}
    assert issues.status is QualityStatus.QUARANTINED
    assert {
        "OUT_OF_ORDER",
        "DUPLICATE_TIMESTAMP",
        "FUTURE_TIMESTAMP",
        "MIXED_CURRENCY",
        "MIXED_ADJUSTMENT",
    } <= codes
    mismatch = check_series([_bar(8)], now=NOW, expected_currency="BRL")
    assert [issue.code for issue in mismatch.issues] == ["CURRENCY_MISMATCH"]


def test_cross_source_comparison_never_picks_a_side() -> None:
    agree = compare_sources(Decimal("10"), Decimal("10.01"), tolerance_ratio=Decimal("0.005"))
    diverge = compare_sources(Decimal("10"), Decimal("10.2"), tolerance_ratio=Decimal("0.005"))
    assert (agree.status, diverge.status) == ("AGREE", "DIVERGENT")
    assert diverge.difference_ratio == Decimal("0.02")
