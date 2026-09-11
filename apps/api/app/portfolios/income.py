"""Read-only portfolio income and chart-marker guardrails for Day 27."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Mapping


class IncomeStatus(StrEnum):
    APPLIED = "APPLIED"
    PENDING = "PENDING"
    UNAVAILABLE = "UNAVAILABLE"


def derive_income_status(
    *,
    payment_date: date | None,
    today: date,
    has_ledger_receipt: bool,
    corporate_status: str,
) -> IncomeStatus:
    """Derive display state without changing ledger or performance mathematics."""
    if corporate_status in {"CANCELLED", "UNAVAILABLE"} and not has_ledger_receipt:
        return (
            IncomeStatus.UNAVAILABLE
            if corporate_status == "UNAVAILABLE"
            else IncomeStatus.PENDING
        )
    if has_ledger_receipt or (payment_date is not None and payment_date <= today):
        return IncomeStatus.APPLIED
    return IncomeStatus.PENDING


def validate_marker_references(
    markers: list[Mapping[str, str]],
    ledger_event_ids: set[str],
    corporate_action_ids: set[str],
) -> None:
    """Fail closed when a visual marker does not point to a persisted source row."""
    for marker in markers:
        source_type = marker.get("source_type")
        source_id = marker.get("source_id")
        if source_type == "LEDGER_EVENT" and source_id in ledger_event_ids:
            continue
        if source_type == "CORPORATE_ACTION" and source_id in corporate_action_ids:
            continue
        raise ValueError(f"orphan marker: {source_type}:{source_id}")
