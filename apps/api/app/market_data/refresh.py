"""Internal, idempotent refresh orchestration.

This module is deliberately not mounted as a public route.  It validates the
licensing envelope before invoking an adapter and only coordinates cache
invalidation; persistence is owned by the ingestion pipeline.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable

from app.market_data.cache import CacheKey, DistributedLock
from app.providers.demo import DemoProvider
from app.providers.licensing import DatasetAccessRequest, LicenseService
from app.providers.models import (
    DataLevel,
    ProviderCapability,
    ProviderDatasetRef,
    ProviderResult,
)


class RefreshStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    SKIPPED_LICENSE_BLOCKED = "SKIPPED_LICENSE_BLOCKED"
    SKIPPED_LOCKED = "SKIPPED_LOCKED"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class RefreshRequest:
    dataset: ProviderDatasetRef
    canonical_id: str
    capability: ProviderCapability
    data_level: DataLevel = DataLevel.DEMO
    purpose: str = "internal_refresh"
    modality: str = "cache"
    environment: str = "local"
    plan: str | None = None


@dataclass(frozen=True)
class RefreshResult:
    status: RefreshStatus
    job_id: str
    request_id: str
    cache_key: str
    error_code: str | None = None


class RefreshService:
    def __init__(
        self,
        *,
        provider: Any | Callable[[str], ProviderResult[Any]] | None = None,
        cache: Any,
        licensing: LicenseService | None = None,
        lock_backend: Any | None = None,
    ) -> None:
        self.provider = provider
        self.cache = cache
        self.licensing = licensing or LicenseService()
        self.lock_backend = lock_backend or cache
        self._runs: dict[str, RefreshResult] = {}

    @staticmethod
    def _job_id(request: RefreshRequest) -> str:
        value = ":".join(
            (request.dataset.provider, request.dataset.dataset,
             request.capability.value, request.canonical_id)
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]

    def _cache_key(self, request: RefreshRequest) -> str:
        if request.capability is ProviderCapability.LATEST_QUOTE:
            return CacheKey.quote(request.dataset.dataset, request.canonical_id)
        return CacheKey.lock(request.dataset.dataset, request.canonical_id)

    def refresh(self, request: RefreshRequest) -> RefreshResult:
        job_id = self._job_id(request)
        cache_key = self._cache_key(request)
        previous = self._runs.get(job_id)
        if previous is not None and previous.status is RefreshStatus.SUCCESS:
            return previous
        decision = self.licensing.decide_access(
            DatasetAccessRequest(
                dataset=request.dataset,
                capability=request.capability,
                purpose=request.purpose,
                modality=request.modality,
                environment=request.environment,
                data_level=request.data_level,
                plan=request.plan,
            )
        )
        if not decision.allowed:
            result = RefreshResult(
                RefreshStatus.SKIPPED_LICENSE_BLOCKED,
                job_id,
                job_id,
                cache_key,
                decision.code,
            )
            self._runs[job_id] = result
            return result
        lock = DistributedLock(
            self.lock_backend,
            CacheKey.lock(request.dataset.dataset, request.canonical_id),
            owner=job_id,
        )
        if not lock.acquire():
            return RefreshResult(RefreshStatus.SKIPPED_LOCKED, job_id, job_id, cache_key)
        try:
            result = self._invoke(request)
            if not isinstance(result, ProviderResult):
                raise TypeError("provider must return ProviderResult")
            if result.provenance.data_level is not request.data_level:
                raise ValueError("provider result data level mismatch")
            # Invalidate only the affected identity. The ingestion writer owns
            # durable persistence and a subsequent read repopulates the cache.
            self.cache.delete(cache_key)
            outcome = RefreshResult(RefreshStatus.SUCCESS, job_id, job_id, cache_key)
            self._runs[job_id] = outcome
            return outcome
        except Exception:
            return RefreshResult(RefreshStatus.FAILED, job_id, job_id, cache_key, "REFRESH_FAILED")
        finally:
            lock.release()

    def _invoke(self, request: RefreshRequest) -> ProviderResult[Any]:
        if self.provider is None:
            if request.data_level is not DataLevel.DEMO:
                raise RuntimeError("provider is required for non-demo refresh")
            provider = DemoProvider()
            method = getattr(provider, request.capability.value)
            return method(request.canonical_id)
        if callable(self.provider):
            return self.provider(request.canonical_id)
        method = getattr(self.provider, request.capability.value)
        return method(request.canonical_id)
