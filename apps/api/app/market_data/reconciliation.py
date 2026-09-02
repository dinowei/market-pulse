"""Deterministic reconciliation checks for market-data coverage and provenance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable

from app.providers.models import DataLevel, Freshness


@dataclass(frozen=True)
class ReconciliationRecord:
    canonical_id: str
    trading_date: date
    source: str
    data_level: DataLevel
    freshness: Freshness
    source_timestamp: datetime | None
    collected_at: datetime | None
    value: Decimal | None
    license_status: str
    license_evidence: bool
    quarantined: bool = False


@dataclass(frozen=True)
class ReconciliationResult:
    status: str
    canonical_id: str
    expected_days: tuple[date, ...]
    gaps: tuple[date, ...]
    provenance_issues: tuple[str, ...]
    blocked_records: int
    quarantined_records: int


def reconcile_market_data(
    *,
    canonical_id: str,
    start_date: date,
    end_date: date,
    records: Iterable[ReconciliationRecord],
    holidays: frozenset[date] = frozenset(),
) -> ReconciliationResult:
    expected = tuple(
        day for ordinal in range((end_date - start_date).days + 1)
        if (day := date.fromordinal(start_date.toordinal() + ordinal)).weekday() < 5
        and day not in holidays
    )
    by_day: dict[date, ReconciliationRecord] = {}
    blocked = quarantined = 0
    issues: list[str] = []
    for record in records:
        if record.license_status != "PUBLIC_APPROVED" and record.license_status != "DEMO_SYNTHETIC":
            blocked += 1
            continue
        if not record.license_evidence:
            issues.append(f"{record.trading_date.isoformat()}:missing_license_evidence")
        if record.quarantined:
            quarantined += 1
            continue
        if not record.source or record.source_timestamp is None or record.collected_at is None:
            issues.append(f"{record.trading_date.isoformat()}:missing_provenance")
        by_day[record.trading_date] = record
    gaps = tuple(day for day in expected if day not in by_day)
    if blocked:
        status = "BLOCKED"
    elif gaps or issues or quarantined:
        status = "GAP"
    else:
        status = "COMPLETE"
    return ReconciliationResult(
        status, canonical_id, expected, gaps, tuple(issues), blocked, quarantined
    )
