from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.contracts import ContentType
from app.market_data.cache import CacheAsideService, CacheEnvelope, MemoryCacheBackend
from app.providers.gateway import ProviderGateway
from app.providers.licensing import (
    DatasetAccessRequest,
    LicenseDecision,
    LicenseService,
)
from app.providers.models import DataLevel, Freshness, ProviderCapability, ProviderDatasetRef
from app.providers.normalization import normalize_ohlcv

UTC = timezone.utc


def approved_dataset(**overrides: object) -> ProviderDatasetRef:
    values: dict[str, object] = {
        "provider": "demo",
        "dataset": "demo-quotes",
        "license_status": "PUBLIC_APPROVED",
        "public_approved": True,
        "evidence": True,
        "plan": "demo-local",
        "endpoint": "latest_quote",
        "purpose": "internal_refresh",
        "modality": "cache",
        "environment": "local",
    }
    values.update(overrides)
    return ProviderDatasetRef(**values)


def request(dataset: ProviderDatasetRef) -> DatasetAccessRequest:
    return DatasetAccessRequest(
        dataset=dataset,
        capability=ProviderCapability.LATEST_QUOTE,
        purpose="internal_refresh",
        modality="cache",
        environment="local",
        data_level=DataLevel.DEMO,
    )


def envelope(*, license_status: str = "PUBLIC_APPROVED", approved: bool = True) -> CacheEnvelope:
    now = datetime(2026, 9, 2, 12, tzinfo=UTC)
    return CacheEnvelope(
        value={"price": Decimal("10.00")},
        source="demo",
        dataset="demo-quotes",
        data_level=DataLevel.DEMO,
        freshness=Freshness.STALE,
        source_timestamp=now,
        collected_at=now,
        cached_at=now,
        fresh_until=now,
        stale_until=now,
        currency="BRL",
        license_status=license_status,
        license_evidence=approved,
    )


def test_content_type_uses_explicit_canonical_name():
    assert ContentType.THIRD_PARTY_CONSENSUS.value == "THIRD_PARTY_CONSENSUS"
    assert "CONSENSUS" not in {item.value for item in ContentType}


def test_access_decision_requires_all_dimensions_and_default_denies():
    service = LicenseService()
    assert service.decide_access(request(approved_dataset())).allowed
    missing_plan = approved_dataset(plan=None)
    decision = service.decide_access(request(missing_plan))
    assert decision.decision is LicenseDecision.BLOCK
    assert decision.code == "LICENSE_DIMENSION_MISSING"
    assert (
        service.decide_access(request(approved_dataset(license_status="UNREVIEWED"))).decision
        is LicenseDecision.BLOCK
    )


def test_provider_dataset_ref_preserves_legacy_simple_decision():
    assert (
        LicenseService().decide(
            ProviderDatasetRef(provider="demo", dataset="demo", license_status="UNREVIEWED")
        )
        is LicenseDecision.BLOCK
    )


def test_provider_normalization_rejects_missing_currency_instead_of_assuming_usd():
    with pytest.raises(ValueError, match="currency"):
        normalize_ohlcv(
            {"t": "2026-09-02T12:00:00Z", "o": "9", "h": "11", "l": "8", "c": "10"},
            "equity.br.b3.petr4",
            "demo",
            "quotes",
        )


def test_cache_does_not_serve_unapproved_real_envelope():
    backend = MemoryCacheBackend()
    key = "market_data:quote:quotes:equity.br.b3.petr4"
    backend.set(key, envelope(license_status="UNREVIEWED", approved=False), ttl=60)
    result = CacheAsideService(backend).get_or_load(
        key, lambda: pytest.fail("blocked cache must not load")
    )
    assert result.freshness is Freshness.UNAVAILABLE
    assert result.data_level is DataLevel.DEMO


def test_gateway_strict_access_blocks_capability_mismatch_before_provider():
    class Provider:
        capabilities = frozenset({ProviderCapability.LATEST_QUOTE})

        def latest_quote(self, _: str):
            raise AssertionError("provider must not be called")

    gateway = ProviderGateway([Provider()])
    blocked = approved_dataset(endpoint="historical_bars")
    with pytest.raises(PermissionError):
        gateway.request(
            ProviderCapability.LATEST_QUOTE,
            blocked,
            "equity.br.b3.petr4",
            purpose="internal_refresh",
            modality="cache",
            environment="local",
        )
