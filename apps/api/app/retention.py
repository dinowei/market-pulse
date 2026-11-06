"""Retention purge for operational records. Never touches the financial ledger.

Dry-run is the default: the routine reports what it would delete and writes
nothing unless the caller explicitly asks for it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psycopg

from app.core.config import get_settings

# Append-only financial and audit records are never purged here. portfolio_events is
# additionally protected by the prevent_immutable_portfolio_event_change trigger, and
# audit_logs retention is a compliance decision this routine deliberately does not take.
PROTECTED_TABLES = frozenset(
    {
        "audit_logs",
        "portfolio_cash_balances",
        "portfolio_daily_valuations",
        "portfolio_events",
        "portfolio_positions",
        "portfolios",
        "sessions",
        "users",
    }
)

# Children before parents: both quarantine tables reference raw_payload_records, so
# purging the parent first would fail on the foreign key.
PURGE_PLAN: tuple[tuple[str, str], ...] = (
    ("market_data_quarantine", "created_at"),
    ("corporate_actions_quarantine", "created_at"),
    ("raw_payload_records", "captured_at"),
    ("web_vital_metrics", "bucket_start"),
)


@dataclass(frozen=True)
class PurgeResult:
    table: str
    column: str
    matched_rows: int
    deleted_rows: int
    remaining_rows: int


class RetentionLimitExceeded(RuntimeError):
    """The number of eligible rows exceeds the operator's explicit safety limit."""


class RetentionCountChanged(RuntimeError):
    """The rows changed while the purge was running; the transaction must roll back."""


def cutoff_for(retention_days: int, now: datetime | None = None) -> datetime:
    if retention_days < 1:
        raise ValueError("retention_days must be at least 1")
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        raise ValueError("reference time must be timezone aware")
    return reference - timedelta(days=retention_days)


def assert_plan_is_safe() -> None:
    """Fail closed if the plan ever names a protected table."""
    for table, _ in PURGE_PLAN:
        if table in PROTECTED_TABLES:
            raise ValueError(f"Refusing to purge protected table: {table}")


def validate_purge_limits(*, dry_run: bool, max_rows: int | None, batch_size: int | None) -> None:
    """Require explicit bounds for writes; dry-runs may omit bounds to inspect counts."""
    if not dry_run and (max_rows is None or batch_size is None):
        raise ValueError("execute_requires_max_rows_and_batch_size")
    if batch_size is not None and max_rows is None:
        raise ValueError("batch_size_requires_max_rows")
    if max_rows is not None and max_rows < 1:
        raise ValueError("max_rows_must_be_at_least_1")
    if batch_size is not None and batch_size < 1:
        raise ValueError("batch_size_must_be_at_least_1")
    if max_rows is not None and batch_size is not None and batch_size > max_rows:
        raise ValueError("batch_size_must_not_exceed_max_rows")


def purge_expired_records(
    *,
    dry_run: bool = True,
    retention_days: int | None = None,
    now: datetime | None = None,
    max_rows: int | None = None,
    batch_size: int | None = None,
    on_before_count: Callable[[str, int], None] | None = None,
) -> list[PurgeResult]:
    """Delete operational rows older than the retention window.

    Deleting by cutoff is naturally idempotent: a second run finds nothing left to
    remove. With dry_run the transaction is rolled back, so counts are measured
    without modifying any row. Apply requires explicit total and per-statement limits;
    rows are counted before any delete and verified again before commit.
    """
    assert_plan_is_safe()
    validate_purge_limits(dry_run=dry_run, max_rows=max_rows, batch_size=batch_size)
    settings = get_settings()
    window = settings.retention_days if retention_days is None else retention_days
    cutoff = cutoff_for(window, now)

    results: list[PurgeResult] = []
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            counts = [
                (
                    table,
                    column,
                    int(
                        cursor.execute(
                            f"SELECT COUNT(*) FROM {table} WHERE {column} < %s", (cutoff,)
                        ).fetchone()[0]
                    ),
                )
                for table, column in PURGE_PLAN
            ]
            total_matched = sum(matched for _, _, matched in counts)
            if on_before_count is not None:
                for table, _, matched in counts:
                    on_before_count(table, matched)

            if max_rows is not None and total_matched > max_rows:
                if dry_run:
                    connection.rollback()
                    return [
                        PurgeResult(table, column, matched, 0, matched)
                        for table, column, matched in counts
                    ]
                raise RetentionLimitExceeded

            for table, column, matched in counts:
                deleted = 0
                if not dry_run and matched:
                    assert batch_size is not None
                    remaining_to_delete = matched
                    while remaining_to_delete:
                        current_batch = min(batch_size, remaining_to_delete)
                        cursor.execute(
                            f"WITH candidates AS ("
                            f"SELECT ctid FROM {table} WHERE {column} < %s "
                            f"ORDER BY {column}, ctid LIMIT %s) "
                            f"DELETE FROM {table} AS target USING candidates "
                            f"WHERE target.ctid = candidates.ctid",
                            (cutoff, current_batch),
                        )
                        batch_deleted = cursor.rowcount
                        if batch_deleted != current_batch:
                            raise RetentionCountChanged
                        deleted += batch_deleted
                        remaining_to_delete -= batch_deleted

                remaining_rows = int(
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE {column} < %s", (cutoff,)
                    ).fetchone()[0]
                )
                if not dry_run and remaining_rows:
                    raise RetentionCountChanged
                results.append(PurgeResult(table, column, matched, deleted, remaining_rows))
        if dry_run:
            connection.rollback()
        else:
            connection.commit()
    return results
