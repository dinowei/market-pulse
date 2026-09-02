"""Controlled, provider-agnostic historical backfill orchestration."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Callable, Iterable

from app.market_data.cache import CacheKey
from app.providers.models import DataLevel


class BackfillStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    LICENSE_BLOCKED = "LICENSE_BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class BackfillRequest:
    canonical_ids: tuple[str, ...]
    start_date: date
    end_date: date
    data_level: DataLevel = DataLevel.DEMO
    license_status: str = "DEMO_SYNTHETIC"
    license_evidence: bool = True
    dataset: str = "demo-quotes"
    timeframe: str = "1d"
    adjustment: str = "raw"

    def __init__(
        self,
        *,
        canonical_ids: Iterable[str],
        start_date: date,
        end_date: date,
        data_level: DataLevel = DataLevel.DEMO,
        license_status: str = "DEMO_SYNTHETIC",
        license_evidence: bool = True,
        dataset: str = "demo-quotes",
        timeframe: str = "1d",
        adjustment: str = "raw",
    ) -> None:
        ids = tuple(canonical_ids)
        if not ids or any(not value.strip() for value in ids):
            raise ValueError("canonical_ids must be explicit and non-empty")
        if any("." not in value for value in ids):
            raise ValueError("canonical_ids must use canonical identity, not ticker-only")
        if len(set(ids)) != len(ids):
            raise ValueError("canonical_ids must be unique")
        if end_date < start_date:
            raise ValueError("end_date must not precede start_date")
        if (end_date - start_date).days + 1 > 31:
            raise ValueError("backfill range exceeds 31 calendar days")
        object.__setattr__(self, "canonical_ids", ids)
        object.__setattr__(self, "start_date", start_date)
        object.__setattr__(self, "end_date", end_date)
        object.__setattr__(self, "data_level", data_level)
        object.__setattr__(self, "license_status", license_status)
        object.__setattr__(self, "license_evidence", license_evidence)
        object.__setattr__(self, "dataset", dataset)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "adjustment", adjustment)


@dataclass(frozen=True)
class BackfillResult:
    status: BackfillStatus
    run_id: str
    total_items: int
    succeeded_items: int
    failed_items: int
    skipped_items: int
    invalidated_keys: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


_RUNS: dict[str, BackfillResult] = {}


def _run_id(request: BackfillRequest) -> str:
    value = "|".join(
        (
            *request.canonical_ids,
            request.start_date.isoformat(),
            request.end_date.isoformat(),
            request.dataset,
        )
    )
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def run_backfill(
    request: BackfillRequest,
    *,
    provider: Callable[[str, date, date], Iterable[Decimal | int | str]] | None = None,
) -> BackfillResult:
    """Run a bounded backfill; provider invocation is denied by default."""
    run_id = _run_id(request)
    previous = _RUNS.get(run_id)
    if previous is not None:
        return previous
    if (
        request.license_status not in {"DEMO_SYNTHETIC", "PUBLIC_APPROVED"}
        or not request.license_evidence
    ):
        result = BackfillResult(
            BackfillStatus.LICENSE_BLOCKED,
            run_id,
            len(request.canonical_ids),
            0,
            0,
            len(request.canonical_ids),
            warnings=("provider and dataset blocked by default deny",),
        )
        _RUNS[run_id] = result
        return result
    if provider is None:
        result = BackfillResult(
            BackfillStatus.FAILED,
            run_id,
            len(request.canonical_ids),
            0,
            len(request.canonical_ids),
            0,
            warnings=("no provider configured; no network operation executed",),
        )
        _RUNS[run_id] = result
        return result
    succeeded = failed = 0
    invalidated: list[str] = []
    for canonical_id in request.canonical_ids:
        try:
            list(provider(canonical_id, request.start_date, request.end_date))
            succeeded += 1
            invalidated.append(
                CacheKey.history(
                    request.dataset, canonical_id, request.timeframe, request.adjustment
                )
            )
        except Exception:
            failed += 1
    status = (
        BackfillStatus.SUCCESS
        if failed == 0
        else (BackfillStatus.PARTIAL if succeeded else BackfillStatus.FAILED)
    )
    result = BackfillResult(
        status, run_id, len(request.canonical_ids), succeeded, failed, 0, tuple(invalidated)
    )
    _RUNS[run_id] = result
    return result
