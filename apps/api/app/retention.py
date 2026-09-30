"""Retention purge for operational records. Never touches the financial ledger.

Dry-run is the default: the routine reports what it would delete and writes
nothing unless the caller explicitly asks for it.
"""

from __future__ import annotations

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


def purge_expired_records(
    *,
    dry_run: bool = True,
    retention_days: int | None = None,
    now: datetime | None = None,
) -> list[PurgeResult]:
    """Delete operational rows older than the retention window.

    Deleting by cutoff is naturally idempotent: a second run finds nothing left to
    remove. With dry_run the transaction is rolled back, so counts are measured
    against the same snapshot a real run would see.
    """
    assert_plan_is_safe()
    settings = get_settings()
    window = settings.retention_days if retention_days is None else retention_days
    cutoff = cutoff_for(window, now)

    results: list[PurgeResult] = []
    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            for table, column in PURGE_PLAN:
                matched = cursor.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {column} < %s", (cutoff,)
                ).fetchone()[0]
                deleted = 0
                if not dry_run and matched:
                    cursor.execute(f"DELETE FROM {table} WHERE {column} < %s", (cutoff,))
                    deleted = cursor.rowcount
                results.append(PurgeResult(table, column, int(matched), int(deleted)))
        if dry_run:
            connection.rollback()
        else:
            connection.commit()
    return results
