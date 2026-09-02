from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.providers.candidate_adapters import BrapiAdapter, ProviderHttpResponse
from app.providers.demo import DemoProvider
from app.providers.models import DataLevel, Freshness, ProviderDatasetRef
from app.providers.normalization import normalize_ohlcv, normalize_quote
from app.providers.raw_payload import RawPayloadRecord, sanitize_payload


def approved() -> ProviderDatasetRef:
    return ProviderDatasetRef(
        provider="brapi",
        dataset="quotes",
        license_status="PUBLIC_APPROVED",
        public_approved=True,
        evidence=True,
    )


def test_quote_payload_is_normalized_to_decimal_and_canonical_identity() -> None:
    result = normalize_quote(
        {
            "symbol": "PETR4",
            "price": "38.20",
            "currency": "BRL",
            "timestamp": "2026-09-01T12:00:00Z",
        },
        "equity.br.b3.petr4",
        "brapi",
        "quotes",
    )
    assert result.canonical_id == "equity.br.b3.petr4"
    assert result.price == Decimal("38.20")
    assert result.source_timestamp.tzinfo is not None


def test_history_payload_normalizes_ohlcv_and_rejects_invalid_data() -> None:
    result = normalize_ohlcv(
        {
            "t": "2026-09-01T12:00:00Z",
            "o": "10",
            "h": "11",
            "l": "9",
            "c": "10.5",
            "v": "100",
            "currency": "BRL",
        },
        "equity.br.b3.petr4",
        "brapi",
        "history",
    )
    assert result.close == Decimal("10.5")
    assert result.volume == Decimal("100")
    with pytest.raises(ValueError):
        normalize_ohlcv({"t": "bad", "o": "x"}, "x", "p", "d")


def test_candidate_adapter_maps_http_errors_without_network() -> None:
    adapter = BrapiAdapter(dataset=approved(), token=None)
    with pytest.raises(Exception, match="not configured"):
        adapter.latest_quote("equity.br.b3.petr4")
    response = ProviderHttpResponse(status_code=429, payload={"message": "slow"})
    with pytest.raises(Exception, match="rate limit"):
        adapter.raise_for_status(response, request_id="req-1")


def test_raw_payload_is_sanitized_hashed_and_never_retains_auth() -> None:
    safe = sanitize_payload({"Authorization": "Bearer secret", "api_key": "real", "price": "1"})
    assert "secret" not in str(safe)
    record = RawPayloadRecord.from_payload(
        provider="brapi",
        dataset="quotes",
        capability="latest_quote",
        request_id="req-1",
        payload=safe,
        captured_at=datetime.now(timezone.utc),
    )
    assert record.payload_hash
    assert record.status == "NORMALIZED"


def test_demo_provider_covers_quote_history_fx_metadata_and_events() -> None:
    provider = DemoProvider()
    assert (
        provider.historical_bars(
            "equity.br.b3.petr4", datetime.now(timezone.utc), datetime.now(timezone.utc)
        ).provenance.data_level
        is DataLevel.DEMO
    )
    assert provider.fx_rate("USD", "BRL").provenance.freshness is Freshness.STALE
    assert provider.instrument_metadata("equity.br.b3.petr4").value["canonical_id"]
    assert provider.dividends("equity.br.b3.petr4").provenance.data_level is DataLevel.DEMO
    assert provider.corporate_actions("equity.br.b3.petr4").value
