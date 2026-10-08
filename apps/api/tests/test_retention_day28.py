"""Retention purge guardrails. The plan assertions need no database."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import Settings
from app.retention import (
    PROTECTED_TABLES,
    PURGE_PLAN,
    assert_plan_is_safe,
    cutoff_for,
    purge_expired_records,
)


def test_ledger_and_audit_trail_are_never_in_the_purge_plan() -> None:
    planned = {table for table, _ in PURGE_PLAN}
    assert "portfolio_events" in PROTECTED_TABLES
    assert "audit_logs" in PROTECTED_TABLES
    assert planned.isdisjoint(PROTECTED_TABLES)
    assert_plan_is_safe()


def test_quarantine_is_purged_before_the_raw_payloads_it_references() -> None:
    order = [table for table, _ in PURGE_PLAN]
    parent = order.index("raw_payload_records")
    assert order.index("market_data_quarantine") < parent
    assert order.index("corporate_actions_quarantine") < parent


def test_cutoff_respects_the_window_and_requires_an_aware_reference() -> None:
    now = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
    assert cutoff_for(90, now) == now - timedelta(days=90)

    with pytest.raises(ValueError):
        cutoff_for(0, now)
    with pytest.raises(ValueError):
        cutoff_for(90, datetime(2026, 9, 30, 12, 0))


def test_retention_window_is_configurable_and_defaults_to_ninety_days() -> None:
    assert Settings().retention_days == 90
    assert Settings(retention_days=30).retention_days == 30


def test_purge_is_dry_run_unless_the_caller_opts_out() -> None:
    import inspect

    signature = inspect.signature(purge_expired_records)
    assert signature.parameters["dry_run"].default is True
