"""The retention command: dry-run by default, never leaks connection details.

No database is used: purge_expired_records is replaced by a recorder.
"""

import pytest

from app.cli import retention as cli
from app.core.config import get_settings
from app.retention import PurgeResult


def _record(monkeypatch, calls: list[dict], *, raises: Exception | None = None) -> None:
    def fake(**kwargs):
        calls.append(kwargs)
        if raises is not None:
            raise raises
        results = [
            PurgeResult(
                "market_data_quarantine",
                "created_at",
                4,
                0 if kwargs["dry_run"] else 4,
                4 if kwargs["dry_run"] else 0,
            ),
            PurgeResult(
                "web_vital_metrics",
                "bucket_start",
                1,
                0 if kwargs["dry_run"] else 1,
                1 if kwargs["dry_run"] else 0,
            ),
        ]
        callback = kwargs.get("on_before_count")
        if callback is not None:
            for result in results:
                callback(result.table, result.matched_rows)
        return results

    monkeypatch.setattr(cli, "purge_expired_records", fake)


def test_default_run_is_a_dry_run(monkeypatch, capsys) -> None:
    calls: list[dict] = []
    _record(monkeypatch, calls)

    assert cli.main([]) == 0

    assert [call["dry_run"] for call in calls] == [True]
    out = capsys.readouterr().out
    assert "mode=dry-run" in out
    assert "RETENTION_BEFORE table=market_data_quarantine matched=4" in out
    assert (
        "RETENTION_AFTER table=market_data_quarantine column=created_at remaining=4 deleted=0"
        in out
    )
    assert "RETENTION_OK mode=dry-run" in out


def test_explicit_dry_run_flag_is_the_same_as_the_default(monkeypatch) -> None:
    calls: list[dict] = []
    _record(monkeypatch, calls)

    assert cli.main(["--dry-run"]) == 0

    assert [call["dry_run"] for call in calls] == [True]


def test_execute_must_be_asked_for_explicitly(monkeypatch, capsys) -> None:
    calls: list[dict] = []
    _record(monkeypatch, calls)

    assert cli.main(["--execute", "--max-rows", "10", "--batch-size", "5"]) == 0

    assert [call["dry_run"] for call in calls] == [False]
    out = capsys.readouterr().out
    assert "mode=execute" in out
    assert (
        "RETENTION_AFTER table=market_data_quarantine column=created_at remaining=0 deleted=4"
        in out
    )


def test_dry_run_and_execute_cannot_be_combined(monkeypatch) -> None:
    calls: list[dict] = []
    _record(monkeypatch, calls)

    with pytest.raises(SystemExit) as stopped:
        cli.main(["--dry-run", "--execute"])

    assert stopped.value.code == 2
    assert calls == []


def test_execute_requires_explicit_limits_before_touching_the_database(monkeypatch, capsys) -> None:
    calls: list[dict] = []
    _record(monkeypatch, calls)

    assert cli.main(["--execute"]) == 2

    assert calls == []
    assert "execute_requires_max_rows_and_batch_size" in capsys.readouterr().err


def test_dry_run_with_a_maximum_reports_an_anomaly_without_applying(monkeypatch, capsys) -> None:
    calls: list[dict] = []
    _record(monkeypatch, calls)

    assert cli.main(["--dry-run", "--max-rows", "4"]) == 2

    assert calls[0]["dry_run"] is True
    captured = capsys.readouterr()
    assert "RETENTION_BEFORE" in captured.out
    assert "RETENTION_ABORTED reason=matched_rows_exceed_max_rows" in captured.err
    assert "RETENTION_OK" not in captured.out


def test_retention_window_comes_from_the_flag_or_the_setting(monkeypatch) -> None:
    calls: list[dict] = []
    _record(monkeypatch, calls)

    cli.main([])
    cli.main(["--retention-days", "30"])

    assert calls[0]["retention_days"] == get_settings().retention_days
    assert calls[1]["retention_days"] == 30


def test_invalid_window_aborts_before_touching_the_database(monkeypatch, capsys) -> None:
    calls: list[dict] = []
    _record(monkeypatch, calls)

    assert cli.main(["--retention-days", "0"]) == 2

    assert calls == []
    assert "RETENTION_ABORTED" in capsys.readouterr().err


def test_a_plan_naming_a_protected_table_aborts_before_any_deletion(monkeypatch, capsys) -> None:
    calls: list[dict] = []
    _record(monkeypatch, calls)
    monkeypatch.setattr("app.retention.PURGE_PLAN", (("audit_logs", "occurred_at"),))

    assert cli.main(["--execute", "--max-rows", "10", "--batch-size", "5"]) == 2

    assert calls == []
    assert "plan_names_a_protected_table" in capsys.readouterr().err


def test_the_report_states_that_the_ledger_and_audit_trail_are_out_of_the_plan(
    monkeypatch, capsys
) -> None:
    _record(monkeypatch, [])

    cli.main([])

    out = capsys.readouterr().out
    assert "audit_logs_in_plan=false" in out
    assert "portfolio_events_in_plan=false" in out
    protected = next(line for line in out.splitlines() if line.startswith("protected_tables="))
    assert "audit_logs" in protected and "portfolio_events" in protected


def test_output_and_failures_never_expose_connection_details(monkeypatch, capsys) -> None:
    # Built by concatenation: a literal credential-shaped URL would trip the secret scanner.
    leaked = "connection to " + "postgresql" + "://someone:" + "hunter2@db.invalid failed"
    _record(monkeypatch, [], raises=RuntimeError(leaked))

    assert cli.main(["--execute", "--max-rows", "10", "--batch-size", "5"]) == 1

    captured = capsys.readouterr()
    everything = captured.out + captured.err
    assert "RETENTION_FAILED error_type=RuntimeError" in captured.err
    assert "hunter2" not in everything and "someone" not in everything
    assert "postgresql://" not in everything and "@" not in everything
