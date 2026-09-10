"""Reset is a disposable database lifecycle, never a trigger bypass."""

import os
from types import SimpleNamespace

import pytest


def test_reset_requires_separate_recreation_authorization_before_io(monkeypatch):
    from app.demo.operations import reset_demo
    from app.demo.safety import DemoSafetyError

    monkeypatch.delenv("MARKET_PULSE_DEMO_ALLOW_RECREATE", raising=False)
    with pytest.raises(DemoSafetyError):
        reset_demo()


def test_bootstrap_requires_separate_lifecycle_authorization_before_io(monkeypatch):
    from app.demo.lifecycle import bootstrap_demo
    from app.demo.safety import DemoSafetyError

    monkeypatch.delenv("MARKET_PULSE_DEMO_ALLOW_RECREATE", raising=False)
    with pytest.raises(DemoSafetyError):
        bootstrap_demo()


def test_bootstrap_creates_only_an_absent_dedicated_demo_database(monkeypatch):
    import app.demo.lifecycle as lifecycle

    monkeypatch.setenv("MARKET_PULSE_DEMO_ALLOW_RECREATE", "true")
    monkeypatch.setattr(
        lifecycle,
        "demo_settings",
        lambda: SimpleNamespace(database_url="postgresql://ignored"),
    )
    monkeypatch.setattr(lifecycle, "_upgrade_to_head", lambda: None)
    monkeypatch.setattr(lifecycle, "_log", lambda *args, **kwargs: None)
    statements: list[str] = []

    class Result:
        def __init__(self, value):
            self.value = value

        def fetchone(self):
            return self.value

    class Admin:
        def execute(self, statement, params=None):
            statements.append(str(statement))
            if "pg_try_advisory_lock" in str(statement):
                return Result((True,))
            if "SELECT 1 FROM pg_database" in str(statement):
                return Result(None)
            return Result(None)

    class MaintenanceConnection:
        def __enter__(self):
            return Admin()

        def __exit__(self, *_):
            return False

    calls = []
    monkeypatch.setattr(
        lifecycle.psycopg,
        "connect",
        lambda *args, **kwargs: calls.append((args, kwargs)) or MaintenanceConnection(),
    )

    report = lifecycle.bootstrap_demo()

    assert report == {
        "status": "DEMO_BOOTSTRAPPED",
        "database": "market_pulse_demo",
        "migrations": "head",
        "primary_database_touched": False,
    }
    assert calls[0][1]["dbname"] == "postgres"
    assert any("CREATE DATABASE market_pulse_demo" in statement for statement in statements)
    assert not any("DROP DATABASE" in statement for statement in statements)


@pytest.mark.parametrize("name", ["market_pulse", "postgres", "market_pulse_demo_backup"])
def test_reset_rejects_any_other_database_before_io(monkeypatch, name):
    from app.demo.operations import reset_demo
    from app.demo.safety import DemoSafetyError

    monkeypatch.setenv("MARKET_PULSE_DEMO_ALLOW_RECREATE", "true")
    monkeypatch.setenv(
        "MARKET_PULSE_DEMO_DATABASE_URL", f"postgresql://demo:local_only@localhost/{name}"
    )
    with pytest.raises(DemoSafetyError):
        reset_demo()


@pytest.mark.skipif(
    os.environ.get("MARKET_PULSE_DEMO_RESET_INTEGRATION") != "true",
    reason="Recreation requires explicit dedicated-local authorization and stopped servers",
)
def test_reset_seed_twice_produces_identical_persisted_logical_state():
    from app.demo.operations import logical_snapshot, reset_demo, seed_demo

    reset_demo()
    assert seed_demo()["status"] == "DEMO_SEEDED"
    first = logical_snapshot()
    reset_demo()
    assert seed_demo()["status"] == "DEMO_SEEDED"
    second = logical_snapshot()
    assert first == second
    assert len(first) == 64
