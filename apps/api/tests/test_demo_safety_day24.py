"""Offline guards: no connection is opened, and no database can be reset here."""

import json
import os
import subprocess
import sys

import pytest


def configuration(**overrides):
    return {
        "APP_ENV": "development",
        "MARKET_PULSE_ENVIRONMENT": "local",
        "MARKET_PULSE_DEMO_ENABLED": "true",
        "MARKET_PULSE_DEMO_DATABASE_URL": (
            "postgresql://demo:local_only@127.0.0.1:5432/market_pulse_demo"
        ),
        **overrides,
    }


def check(values, confirmation="market-pulse/local-demo/v1"):
    from app.demo.safety import validate_demo_target

    return validate_demo_target(values, confirmation=confirmation)


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "[::1]"])
def test_explicit_local_demo_target_is_accepted_without_opening_a_connection(host, monkeypatch):
    import socket

    def no_network(*args, **kwargs):
        pytest.fail("offline configuration guard opened a connection")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    target = check(
        configuration(
            MARKET_PULSE_DEMO_DATABASE_URL=(
                f"postgresql://demo:local_only@{host}:5432/market_pulse_demo"
            )
        )
    )
    assert target.database == "market_pulse_demo"
    assert target.port == 5432
    assert "local_only" not in repr(target)


@pytest.mark.parametrize(
    "field",
    [
        "APP_ENV",
        "MARKET_PULSE_ENVIRONMENT",
        "MARKET_PULSE_DEMO_ENABLED",
        "MARKET_PULSE_DEMO_DATABASE_URL",
    ],
)
def test_missing_barrier_fails_closed(field):
    from app.demo.safety import DemoSafetyError

    values = configuration()
    del values[field]
    with pytest.raises(DemoSafetyError):
        check(values)


@pytest.mark.parametrize(
    "overrides",
    [
        {"APP_ENV": "production"},
        {"APP_ENV": "staging"},
        {"MARKET_PULSE_ENVIRONMENT": "production"},
        {"MARKET_PULSE_ENVIRONMENT": "test"},  # conflicting environments
        {"MARKET_PULSE_DEMO_ENABLED": "false"},
        {"MARKET_PULSE_DEMO_ENABLED": "1"},
        {"MARKET_PULSE_DEMO_ENABLED": ""},
    ],
)
def test_production_ambiguity_and_implicit_flags_are_denied(overrides):
    from app.demo.safety import DemoSafetyError

    with pytest.raises(DemoSafetyError):
        check(configuration(**overrides))


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://demo:local_only@localhost/market_pulse",
        "postgresql://demo:local_only@localhost/market_pulse_demo_backup",
        "postgresql://demo:local_only@db.example/market_pulse_demo",
        "postgresql://demo:local_only@localhost.evil/market_pulse_demo",
        "postgresql://demo:local_only@0.0.0.0/market_pulse_demo",
        "postgresql://demo:local_only@localhost/market_pulse_demo?host=db.example",
        "postgresql://demo:local_only@localhost/market_pulse_demo?options=anything",
        "postgresql://demo:local_only@localhost/market_pulse_demo#fragment",
        "postgresql:///market_pulse_demo",
        "postgresql://localhost/market_pulse_demo",
        "postgresql://demo:local_only@[::1/market_pulse_demo",
        "postgresql://demo:local_only@localhost:bad/market_pulse_demo",
        "postgresql://demo:local_only@localhost:0/market_pulse_demo",
        "postgresql://demo:local_only@localhost/%6darket_pulse_demo",
        "postgresql+psycopg://demo:local_only@localhost/market_pulse_demo",
        "host=localhost dbname=market_pulse_demo",
    ],
)
def test_non_demo_remote_or_ambiguous_connection_is_denied_without_echo(url):
    from app.demo.safety import DemoSafetyError

    with pytest.raises(DemoSafetyError) as error:
        check(configuration(MARKET_PULSE_DEMO_DATABASE_URL=url))
    assert url not in str(error.value)
    assert "local_only" not in str(error.value)
    assert "postgresql://" not in str(error.value)


def test_internal_confirmation_is_required_and_not_read_from_environment():
    from app.demo.safety import DemoSafetyError

    with pytest.raises(DemoSafetyError):
        check(configuration(DEMO_CONFIRMATION="market-pulse/local-demo/v1"), confirmation="")


def test_main_database_url_is_never_a_fallback():
    from app.demo.safety import DemoSafetyError

    values = configuration()
    values["MARKET_PULSE_DATABASE_URL"] = values.pop("MARKET_PULSE_DEMO_DATABASE_URL")
    with pytest.raises(DemoSafetyError):
        check(values)


@pytest.mark.parametrize(
    "key",
    [
        "PGHOST",
        "PGHOSTADDR",
        "PGPORT",
        "PGDATABASE",
        "PGUSER",
        "PGPASSWORD",
        "PGSERVICE",
        "PGSERVICEFILE",
        "PGPASSFILE",
        "PGOPTIONS",
    ],
)
def test_libpq_environment_overrides_are_denied(key):
    from app.demo.safety import DemoSafetyError

    with pytest.raises(DemoSafetyError):
        check(configuration(**{key: "ambiguous-setting"}))


def test_cli_reports_only_configuration_validation_not_database_readiness():
    result = subprocess.run(
        [sys.executable, "-m", "app.demo", "check-target"],
        env={**os.environ, **configuration()},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "CONFIGURATION_ONLY"
    assert report["database"] == "market_pulse_demo"
    assert report["database_connected"] is False
    assert report["writes_performed"] is False
    assert "local_only" not in result.stdout + result.stderr


def test_cli_refuses_main_database_with_safe_error():
    result = subprocess.run(
        [sys.executable, "-m", "app.demo", "check-target"],
        env={
            **os.environ,
            **configuration(
                MARKET_PULSE_DEMO_DATABASE_URL=(
                    "postgresql://demo:local_only@127.0.0.1/market_pulse"
                )
            ),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stderr)["code"] == "DEMO_TARGET_DENIED"
    assert "local_only" not in result.stdout + result.stderr


def test_cli_offline_dataset_report_does_not_claim_seed_or_reset_success():
    result = subprocess.run(
        [sys.executable, "-m", "app.demo", "validate-data"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "OFFLINE_DATASET_ONLY"
    assert report["writes_performed"] is False
    assert report["persistence_gate"] == "NOT_RUN"
    assert report["counts"]["instruments"] == 11
    assert report["counts"]["portfolios"] == 2
    assert len(report["fingerprint"]) == 64


def test_cli_invalid_argument_never_echoes_connection_or_password():
    argument = "postgresql://demo:local_only@127.0.0.1/market_pulse"
    result = subprocess.run(
        [sys.executable, "-m", "app.demo", argument],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert argument not in result.stdout + result.stderr
    assert "local_only" not in result.stdout + result.stderr


def test_seed_cli_denies_production_before_database_or_network():
    result = subprocess.run(
        [sys.executable, "-m", "app.demo", "seed_demo"],
        env={**os.environ, **configuration(APP_ENV="production")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stderr)["code"] == "DEMO_TARGET_DENIED"
    assert "postgresql://" not in result.stdout + result.stderr


def test_seed_empty_database_check_rejects_populated_auxiliary_table():
    from app.demo.operations import _assert_seed_database_empty
    from app.demo.safety import DemoSafetyError

    class Result:
        def __init__(self, value):
            self.value = value

        def fetchall(self):
            return self.value

        def fetchone(self):
            return self.value

    class Connection:
        def execute(self, statement):
            if "pg_tables" in str(statement):
                return Result([("public", "exchanges")])
            return Result((1,))

    with pytest.raises(DemoSafetyError):
        _assert_seed_database_empty(Connection())
