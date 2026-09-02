from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.market_data.cache import CacheEnvelope, CacheKey, MemoryCacheBackend
from app.market_data.refresh import RefreshRequest, RefreshService, RefreshStatus
from app.providers.models import (
    DataLevel,
    Freshness,
    ProviderCapability,
    ProviderDatasetRef,
    ProviderProvenance,
    ProviderResult,
)

UTC = timezone.utc


def dataset(status: str = "PUBLIC_APPROVED") -> ProviderDatasetRef:
    return ProviderDatasetRef(
        provider="demo",
        dataset="demo-quotes",
        license_status=status,
        public_approved=status == "PUBLIC_APPROVED",
        evidence=status == "PUBLIC_APPROVED",
        plan="demo-local",
        endpoint="latest_quote",
        purpose="internal_refresh",
        modality="cache",
        environment="local",
    )


def result() -> ProviderResult[Decimal]:
    now = datetime(2026, 9, 2, 12, tzinfo=UTC)
    return ProviderResult(
        value=Decimal("10.00"),
        provenance=ProviderProvenance(
            provider="demo",
            dataset="demo-quotes",
            source="demo",
            source_timestamp=now,
            collected_at=now,
            data_level=DataLevel.DEMO,
            freshness=Freshness.STALE,
            currency="BRL",
        ),
    )


def request(status: str = "PUBLIC_APPROVED") -> RefreshRequest:
    return RefreshRequest(
        dataset=dataset(status),
        canonical_id="equity.br.b3.petr4",
        capability=ProviderCapability.LATEST_QUOTE,
        data_level=DataLevel.DEMO,
    )


def test_unapproved_refresh_is_skipped_without_calling_provider():
    calls = 0

    def provider(_: str):
        nonlocal calls
        calls += 1
        return result()

    service = RefreshService(provider=provider, cache=MemoryCacheBackend())
    outcome = service.refresh(request("UNREVIEWED"))
    assert outcome.status is RefreshStatus.SKIPPED_LICENSE_BLOCKED
    assert calls == 0


def test_demo_refresh_is_idempotent_and_invalidates_only_related_key():
    backend = MemoryCacheBackend()
    key = CacheKey.quote("demo-quotes", "equity.br.b3.petr4")
    other = CacheKey.quote("demo-quotes", "equity.us.nasdaq.aapl")
    now = datetime(2026, 9, 2, 12, tzinfo=UTC)
    cached = CacheEnvelope(
        value=Decimal("9"),
        source="demo",
        dataset="demo-quotes",
        data_level=DataLevel.DEMO,
        freshness=Freshness.STALE,
        source_timestamp=now,
        collected_at=now,
        cached_at=now,
        fresh_until=now,
        stale_until=now + timedelta(hours=1),
        currency="BRL",
    )
    backend.set(key, cached, ttl=600)
    backend.set(other, cached, ttl=600)
    service = RefreshService(provider=lambda _: result(), cache=backend)
    first = service.refresh(request())
    second = service.refresh(request())
    assert first.status is RefreshStatus.SUCCESS
    assert second.status is RefreshStatus.SUCCESS
    assert first.job_id == second.job_id
    assert backend.get(key) is None
    assert backend.get(other) is not None


def test_locked_refresh_returns_controlled_status():
    backend = MemoryCacheBackend()
    service = RefreshService(provider=lambda _: result(), cache=backend)
    request_value = request()
    service.lock_backend.set(CacheKey.lock("demo-quotes", request_value.canonical_id), "other", 60)
    outcome = service.refresh(request_value)
    assert outcome.status is RefreshStatus.SKIPPED_LOCKED
