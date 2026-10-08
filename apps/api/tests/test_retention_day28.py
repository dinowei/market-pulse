"""Retention purge guardrails. The plan assertions need no database."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import Settings
from app.retention import (
    PROTECTED_TABLES,
    PURGE_PLAN,
    RetentionLimitExceeded,
    assert_plan_is_safe,
    cutoff_for,
    purge_expired_records,
    validate_purge_limits,
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


def test_writes_require_explicit_total_and_batch_limits() -> None:
    with pytest.raises(ValueError, match="execute_requires_max_rows_and_batch_size"):
        validate_purge_limits(dry_run=False, max_rows=None, batch_size=None)

    validate_purge_limits(dry_run=False, max_rows=20, batch_size=5)
    validate_purge_limits(dry_run=True, max_rows=None, batch_size=None)


@pytest.mark.parametrize(
    ("max_rows", "batch_size", "reason"),
    [
        (0, 1, "max_rows_must_be_at_least_1"),
        (5, 0, "batch_size_must_be_at_least_1"),
        (5, 6, "batch_size_must_not_exceed_max_rows"),
    ],
)
def test_write_limits_reject_invalid_values(max_rows: int, batch_size: int, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        validate_purge_limits(dry_run=False, max_rows=max_rows, batch_size=batch_size)


class _MemoryCursor:
    def __init__(self, connection: "_MemoryConnection") -> None:
        self.connection = connection
        self.rowcount = -1
        self._row: tuple[int] | None = None
        self.delete_batches: list[int] = []
        self.force_short_delete = False

    def __enter__(self) -> "_MemoryCursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...]) -> "_MemoryCursor":
        import re

        table_match = re.search(r"FROM (\w+)", query)
        if table_match is None:
            raise AssertionError("unrecognized retention query")
        table = table_match.group(1)
        cutoff = params[0]
        if query.startswith("SELECT COUNT(*)"):
            self._row = (sum(value < cutoff for value in self.connection.rows[table]),)
            self.rowcount = -1
            return self

        assert query.startswith("WITH candidates AS (")
        batch_size = int(params[1])
        if self.force_short_delete:
            self.rowcount = batch_size - 1
            self.delete_batches.append(self.rowcount)
            return self
        expired = sorted(value for value in self.connection.rows[table] if value < cutoff)[
            :batch_size
        ]
        for value in expired:
            self.connection.rows[table].remove(value)
        self.rowcount = len(expired)
        self.delete_batches.append(self.rowcount)
        return self

    def fetchone(self) -> tuple[int] | None:
        return self._row


class _MemoryConnection:
    def __init__(self, rows: dict[str, list[datetime]]) -> None:
        self.rows = rows
        self.cursor_instance = _MemoryCursor(self)
        self.did_commit = False
        self.did_rollback = False

    def __enter__(self) -> "_MemoryConnection":
        return self

    def __exit__(self, exc_type: object, *_args: object) -> None:
        if exc_type is not None:
            self.rollback()

    def cursor(self) -> _MemoryCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.did_commit = True

    def rollback(self) -> None:
        self.did_rollback = True


def _empty_retention_rows() -> dict[str, list[datetime]]:
    return {table: [] for table, _ in PURGE_PLAN}


def test_execute_deletes_in_bounded_batches_and_records_before_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import retention

    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    rows = _empty_retention_rows()
    rows["market_data_quarantine"] = [now - timedelta(days=120) for _ in range(5)]
    rows["market_data_quarantine"].append(now - timedelta(days=1))
    connection = _MemoryConnection(rows)
    monkeypatch.setattr(retention.psycopg, "connect", lambda _url: connection)
    monkeypatch.setattr(retention, "get_settings", lambda: Settings())
    before: list[tuple[str, int]] = []

    results = retention.purge_expired_records(
        dry_run=False,
        retention_days=90,
        now=now,
        max_rows=5,
        batch_size=2,
        on_before_count=lambda table, count: before.append((table, count)),
    )

    purged = next(result for result in results if result.table == "market_data_quarantine")
    assert before[0] == ("market_data_quarantine", 5)
    assert purged.matched_rows == 5
    assert purged.deleted_rows == 5
    assert purged.remaining_rows == 0
    assert connection.cursor_instance.delete_batches == [2, 2, 1]
    assert len(rows["market_data_quarantine"]) == 1
    assert connection.did_commit and not connection.did_rollback


def test_execute_aborts_before_deleting_when_the_count_exceeds_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import retention

    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    rows = _empty_retention_rows()
    rows["market_data_quarantine"] = [now - timedelta(days=120) for _ in range(6)]
    connection = _MemoryConnection(rows)
    monkeypatch.setattr(retention.psycopg, "connect", lambda _url: connection)
    monkeypatch.setattr(retention, "get_settings", lambda: Settings())

    with pytest.raises(RetentionLimitExceeded):
        retention.purge_expired_records(
            dry_run=False,
            retention_days=90,
            now=now,
            max_rows=5,
            batch_size=2,
        )

    assert connection.cursor_instance.delete_batches == []
    assert len(rows["market_data_quarantine"]) == 6
    assert not connection.did_commit and connection.did_rollback


def test_execute_rolls_back_when_a_batch_count_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import retention

    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    rows = _empty_retention_rows()
    rows["market_data_quarantine"] = [now - timedelta(days=120) for _ in range(2)]
    connection = _MemoryConnection(rows)
    connection.cursor_instance.force_short_delete = True
    monkeypatch.setattr(retention.psycopg, "connect", lambda _url: connection)
    monkeypatch.setattr(retention, "get_settings", lambda: Settings())

    with pytest.raises(retention.RetentionCountChanged):
        retention.purge_expired_records(
            dry_run=False,
            retention_days=90,
            now=now,
            max_rows=5,
            batch_size=2,
        )

    assert len(rows["market_data_quarantine"]) == 2
    assert not connection.did_commit and connection.did_rollback
