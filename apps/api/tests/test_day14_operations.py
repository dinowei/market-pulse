from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.market_data.backfill import BackfillRequest, BackfillStatus, run_backfill
from app.market_data.reconciliation import (
    ReconciliationRecord,
    reconcile_market_data,
)
from app.providers.models import DataLevel, Freshness


def _record(day: date, *, source: str = "demo", approved: bool = True):
    now = datetime(2026, 9, 2, 12, tzinfo=timezone.utc)
    return ReconciliationRecord(
        canonical_id="equity.br.b3.petr4",
        trading_date=day,
        source=source,
        data_level=DataLevel.DEMO,
        freshness=Freshness.FRESH,
        source_timestamp=now,
        collected_at=now,
        value=Decimal("10.00"),
        license_status="PUBLIC_APPROVED" if approved else "UNREVIEWED",
        license_evidence=approved,
    )


def test_backfill_request_requires_explicit_unique_canonical_ids_and_bounded_dates():
    request = BackfillRequest(
        canonical_ids=["equity.br.b3.petr4"],
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 5),
    )
    assert request.canonical_ids == ("equity.br.b3.petr4",)
    with pytest.raises(ValueError):
        BackfillRequest(
            canonical_ids=["PETR4"],
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
        )
    with pytest.raises(ValueError):
        BackfillRequest(
            canonical_ids=["equity.br.b3.petr4", "equity.br.b3.petr4"],
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
        )


def test_backfill_is_idempotent_and_blocks_unapproved_before_provider_call():
    calls: list[str] = []

    def provider(canonical_id: str, _start: date, _end: date):
        calls.append(canonical_id)
        return []

    request = BackfillRequest(
        canonical_ids=["equity.br.b3.petr4"],
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 2),
        data_level=DataLevel.DEMO,
        license_status="UNREVIEWED",
        license_evidence=False,
    )
    first = run_backfill(request, provider=provider)
    second = run_backfill(request, provider=provider)
    assert first.status is BackfillStatus.LICENSE_BLOCKED
    assert second.status is BackfillStatus.LICENSE_BLOCKED
    assert calls == []


def test_backfill_reports_partial_failures_and_granular_invalidations():
    def provider(canonical_id: str, _start: date, _end: date):
        if canonical_id.endswith("aapl"):
            raise RuntimeError("provider unavailable")
        return [Decimal("10.00")]

    request = BackfillRequest(
        canonical_ids=["equity.br.b3.petr4", "equity.us.nasdaq.aapl"],
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 2),
        data_level=DataLevel.DEMO,
        license_status="DEMO_SYNTHETIC",
        license_evidence=True,
    )
    result = run_backfill(request, provider=provider)
    assert result.status is BackfillStatus.PARTIAL
    assert result.succeeded_items == 1
    assert result.failed_items == 1
    assert result.invalidated_keys == (
        "market_data:history:demo-quotes:equity.br.b3.petr4:1d:raw",
    )


def test_reconciliation_detects_gaps_and_missing_provenance_without_weekend_false_positive():
    complete = reconcile_market_data(
        canonical_id="equity.br.b3.petr4",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 7),
        records=[_record(date(2026, 8, day)) for day in range(3, 8)],
    )
    assert complete.gaps == ()
    weekend = reconcile_market_data(
        canonical_id="equity.br.b3.petr4",
        start_date=date(2026, 8, 8),
        end_date=date(2026, 8, 9),
        records=[],
    )
    assert weekend.gaps == ()
    missing = reconcile_market_data(
        canonical_id="equity.br.b3.petr4",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 5),
        records=[_record(date(2026, 8, 3)), _record(date(2026, 8, 4), source="")],
    )
    assert date(2026, 8, 5) in missing.gaps
    assert missing.provenance_issues


def test_reconciliation_blocks_unapproved_and_quarantined_records():
    result = reconcile_market_data(
        canonical_id="equity.br.b3.petr4",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 3),
        records=[_record(date(2026, 8, 3), approved=False)],
    )
    assert result.status == "BLOCKED"
    assert result.blocked_records == 1


def test_operational_workflow_and_local_script_use_only_explicit_secrets():
    root = Path(__file__).resolve().parents[3]
    workflow = (root / ".github/workflows/market-pulse-refresh.yml").read_text(encoding="utf-8")
    script = (root / "scripts/market_data_refresh.py").read_text(encoding="utf-8")
    assert "workflow_dispatch" in workflow and "schedule" in workflow
    assert "secrets.MARKET_PULSE_API_BASE_URL" in workflow
    assert "secrets.MARKET_PULSE_CRON_SECRET" in workflow
    assert "X-Cron-Secret" in workflow
    assert "DRY_RUN" in workflow
    assert "local_demo_only_change_me" not in workflow + script
    assert "MARKET_PULSE_CRON_SECRET" in script
