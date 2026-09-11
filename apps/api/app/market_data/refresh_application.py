"""Application-layer batch orchestration for the protected refresh route."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import Settings
from app.market_data.cache import MemoryCacheBackend
from app.market_data.refresh import RefreshRequest, RefreshService, RefreshStatus
from app.providers.demo import DemoProvider
from app.providers.models import DataLevel, ProviderCapability, ProviderDatasetRef


class RefreshMode(StrEnum):
    DEMO_ONLY = "DEMO_ONLY"
    LICENSED_ONLY = "LICENSED_ONLY"
    DRY_RUN = "DRY_RUN"


class RefreshBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset: str = Field(min_length=1, max_length=128)
    capability: ProviderCapability
    canonical_ids: list[str] = Field(min_length=1, max_length=100)
    mode: RefreshMode
    max_items: int | None = Field(default=None, ge=1, le=100)

    @field_validator("canonical_ids")
    @classmethod
    def canonical_ids_are_explicit(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("canonical_ids must not contain empty values")
        if len(set(values)) != len(values):
            raise ValueError("canonical_ids must be unique")
        return values


class RefreshBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str
    started_at: datetime
    finished_at: datetime
    total_items: int
    succeeded_items: int
    failed_items: int
    skipped_items: int
    quarantined_items: int
    cache_invalidated_items: int
    data_level: DataLevel
    warnings: list[str]
    request_id: str


_CACHE = MemoryCacheBackend()
_DEMO_SERVICE = RefreshService(provider=DemoProvider(), cache=_CACHE)


def _dataset(payload: RefreshBatchRequest, settings: Settings) -> ProviderDatasetRef:
    if payload.mode is RefreshMode.DEMO_ONLY:
        return ProviderDatasetRef(
            provider="demo",
            dataset=payload.dataset,
            license_status="DEMO_SYNTHETIC",
            public_approved=False,
            evidence=True,
            plan="local-demo",
            endpoint=payload.capability.value,
            purpose="internal_refresh",
            modality="demo",
            environment=settings.environment,
        )
    return ProviderDatasetRef(
        provider="unknown",
        dataset=payload.dataset,
        license_status="UNREVIEWED",
        public_approved=False,
        evidence=False,
        plan=None,
        endpoint=payload.capability.value,
        purpose="internal_refresh",
        modality="licensed",
        environment=settings.environment,
    )


def refresh_market_data(
    *, payload: RefreshBatchRequest, settings: Settings, request_id: str
) -> RefreshBatchResponse:
    started = datetime.now(timezone.utc)
    run_id = str(uuid4())
    ids = payload.canonical_ids[: payload.max_items or settings.refresh_max_items]
    warnings: list[str] = []
    succeeded = failed = skipped = quarantined = invalidated = 0
    data_level = DataLevel.DEMO if payload.mode is RefreshMode.DEMO_ONLY else DataLevel.DELAYED

    if payload.mode is RefreshMode.DRY_RUN:
        warnings.append("dry run: no provider or persistence operation executed")
        finished = datetime.now(timezone.utc)
        return RefreshBatchResponse(
            run_id=run_id,
            status="SUCCESS",
            started_at=started,
            finished_at=finished,
            total_items=len(ids),
            succeeded_items=0,
            failed_items=0,
            skipped_items=len(ids),
            quarantined_items=0,
            cache_invalidated_items=0,
            data_level=data_level,
            warnings=warnings,
            request_id=request_id,
        )

    dataset = _dataset(payload, settings)
    service = (
        _DEMO_SERVICE if payload.mode is RefreshMode.DEMO_ONLY else RefreshService(cache=_CACHE)
    )
    for canonical_id in ids:
        try:
            outcome = service.refresh(
                RefreshRequest(
                    dataset=dataset,
                    canonical_id=canonical_id,
                    capability=payload.capability,
                    data_level=data_level,
                    purpose="internal_refresh",
                    modality="demo" if payload.mode is RefreshMode.DEMO_ONLY else "licensed",
                    environment=settings.environment,
                )
            )
        except Exception:
            failed += 1
            continue
        if outcome.status is RefreshStatus.SUCCESS:
            succeeded += 1
            invalidated += 1
        elif outcome.status is RefreshStatus.SKIPPED_LICENSE_BLOCKED:
            skipped += 1
            warnings.append("one or more items were blocked by licensing")
        elif outcome.status is RefreshStatus.SKIPPED_LOCKED:
            skipped += 1
            warnings.append("one or more items were already being refreshed")
        else:
            failed += 1
    finished = datetime.now(timezone.utc)
    status = "SUCCESS" if failed == 0 else ("PARTIAL" if succeeded or skipped else "FAILED")
    return RefreshBatchResponse(
        run_id=run_id,
        status=status,
        started_at=started,
        finished_at=finished,
        total_items=len(ids),
        succeeded_items=succeeded,
        failed_items=failed,
        skipped_items=skipped,
        quarantined_items=quarantined,
        cache_invalidated_items=invalidated,
        data_level=data_level,
        warnings=sorted(set(warnings)),
        request_id=request_id,
    )
