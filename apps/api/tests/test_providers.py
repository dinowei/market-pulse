from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.providers.demo import DemoProvider
from app.providers.gateway import ProviderGateway
from app.providers.licensing import LicenseDecision, LicenseService
from app.providers.models import (
    DataLevel,
    Freshness,
    ProviderCapability,
    ProviderDatasetRef,
    ProviderProvenance,
    ProviderResult,
)
from app.providers.resilience import RetryPolicy, retry_call


def dataset(status: str = "UNREVIEWED", evidence: bool = False) -> ProviderDatasetRef:
    return ProviderDatasetRef(
        provider="demo",
        dataset="demo-quotes",
        license_status=status,
        public_approved=status == "PUBLIC_APPROVED",
        evidence=evidence,
    )


def provenance() -> ProviderProvenance:
    now = datetime.now(timezone.utc)
    return ProviderProvenance(
        provider="demo",
        dataset="demo-quotes",
        source="local-demo",
        source_timestamp=now,
        collected_at=now,
        data_level=DataLevel.DEMO,
        freshness=Freshness.STALE,
        currency="BRL",
        limitations=("Demonstração local; não representa cotação real.",),
    )


def test_license_service_is_default_deny() -> None:
    service = LicenseService()
    assert service.decide(None) == LicenseDecision.BLOCK
    assert service.decide(dataset()) == LicenseDecision.BLOCK
    assert service.decide(dataset("DEMO", True)) == LicenseDecision.BLOCK
    assert service.decide(dataset("PUBLIC_APPROVED", True)) == LicenseDecision.ALLOW
    assert service.decide(dataset("PUBLIC_APPROVED", False)) == LicenseDecision.BLOCK


def test_provider_result_requires_complete_provenance() -> None:
    result = ProviderResult(value=Decimal("12.34"), provenance=provenance())
    assert result.provenance.data_level is DataLevel.DEMO
    with pytest.raises(ValueError):
        ProviderResult(value=Decimal("1"), provenance=None)  # type: ignore[arg-type]


def test_demo_provider_declares_capability_and_demo_provenance() -> None:
    provider = DemoProvider()
    assert ProviderCapability.LATEST_QUOTE in provider.capabilities
    result = provider.latest_quote("DEMO-ASSET")
    assert result.provenance.data_level is DataLevel.DEMO
    assert result.provenance.freshness is Freshness.STALE
    assert result.value != Decimal("100.00")


def test_gateway_rejects_missing_capability_and_unapproved_dataset() -> None:
    gateway = ProviderGateway([DemoProvider()])
    with pytest.raises(LookupError):
        gateway.request(ProviderCapability.HISTORICAL_BARS, dataset("PUBLIC_APPROVED", True), "X")
    with pytest.raises(PermissionError):
        gateway.request(ProviderCapability.LATEST_QUOTE, dataset(), "X")


def test_gateway_converts_provider_timeout_to_controlled_error() -> None:
    class TimeoutProvider:
        name = "timeout"
        capabilities = frozenset({ProviderCapability.LATEST_QUOTE})

        def latest_quote(self, _: str) -> None:
            raise TimeoutError

    gateway = ProviderGateway([TimeoutProvider()])
    with pytest.raises(Exception, match="timed out"):
        gateway.request(ProviderCapability.LATEST_QUOTE, dataset("PUBLIC_APPROVED", True), "X")


def test_retry_policy_is_bounded_and_uses_explicit_attempts() -> None:
    attempts = 0

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError
        return "ok"

    assert retry_call(operation, RetryPolicy(max_attempts=3, base_delay_seconds=0)) == "ok"
    assert attempts == 3
