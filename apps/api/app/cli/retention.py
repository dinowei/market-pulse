"""Retention purge command.

    python -m app.cli.retention                  # dry-run (default): reports, deletes nothing
    python -m app.cli.retention --execute        # deletes expired operational rows
    python -m app.cli.retention --retention-days 30

Only operational records are purged (see app.retention). The financial ledger and
audit_logs are never touched. Output carries the database NAME only, never the
connection string, and failures report the exception type, never its message, because
database drivers may put the offending value in it.
"""

from __future__ import annotations

import argparse
import sys
from urllib.parse import urlsplit

from app.core.config import get_settings
from app.retention import (
    PROTECTED_TABLES,
    PURGE_PLAN,
    assert_plan_is_safe,
    cutoff_for,
    purge_expired_records,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.retention",
        description="Purge expired operational records. Dry-run unless --execute is given.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be removed and write nothing (this is the default)",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="delete the expired rows; this cannot be undone",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=None,
        help="retention window in days (default: MARKET_PULSE_RETENTION_DAYS)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dry_run = not args.execute

    try:
        assert_plan_is_safe()
    except ValueError:
        print("RETENTION_ABORTED reason=plan_names_a_protected_table", file=sys.stderr)
        return 2

    settings = get_settings()
    days = settings.retention_days if args.retention_days is None else args.retention_days
    try:
        cutoff = cutoff_for(days)
    except ValueError:
        print("RETENTION_ABORTED reason=retention_days_must_be_at_least_1", file=sys.stderr)
        return 2

    database = urlsplit(settings.database_url).path.lstrip("/") or "unknown"
    planned = [table for table, _ in PURGE_PLAN]
    print(f"mode={'dry-run' if dry_run else 'execute'}")
    print(f"database={database}")
    print(f"retention_days={days}")
    print(f"cutoff={cutoff.isoformat()}")
    print(f"plan={','.join(planned)}")
    print(f"protected_tables={','.join(sorted(PROTECTED_TABLES))}")
    print(f"audit_logs_in_plan={'audit_logs' in planned}".lower())
    print(f"portfolio_events_in_plan={'portfolio_events' in planned}".lower())

    try:
        results = purge_expired_records(dry_run=dry_run, retention_days=days)
    except Exception as exc:
        print(f"RETENTION_FAILED error_type={type(exc).__name__}", file=sys.stderr)
        return 1

    for result in results:
        print(
            f"table={result.table} column={result.column} "
            f"matched={result.matched_rows} deleted={result.deleted_rows}"
        )
    print(f"RETENTION_OK mode={'dry-run' if dry_run else 'execute'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
