"""Opt-in tests. Never run writes against the application's primary database."""

import os
from decimal import Decimal

import pytest


def test_seed_refuses_primary_database_before_io(monkeypatch):
    from app.demo.operations import seed_demo
    from app.demo.safety import DemoSafetyError

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("MARKET_PULSE_ENVIRONMENT", "local")
    monkeypatch.setenv("MARKET_PULSE_DEMO_ENABLED", "true")
    monkeypatch.setenv(
        "MARKET_PULSE_DEMO_DATABASE_URL",
        "postgresql://demo:local_only@127.0.0.1:5432/market_pulse",
    )
    with pytest.raises(DemoSafetyError):
        seed_demo()


@pytest.mark.skipif(
    os.environ.get("MARKET_PULSE_DEMO_INTEGRATION") != "true",
    reason="Dedicated DEMO database gate requires explicit opt-in",
)
def test_seed_persists_scenario_via_existing_services_and_is_idempotent():
    import psycopg

    from app.auth.passwords import verify_password
    from app.core.config import get_settings
    from app.demo.operations import DEMO_LOCAL_PASSWORD, seed_demo
    from app.demo.safety import LOCAL_DEMO_CONFIRMATION, validate_demo_target
    from app.editorial.service import PostgresEditorialService
    from app.portfolios.service import PostgresPortfolioService

    validate_demo_target(os.environ, confirmation=LOCAL_DEMO_CONFIRMATION)
    first = seed_demo()
    second = seed_demo()
    assert first["status"] in {"DEMO_SEEDED", "DEMO_ALREADY_SEEDED"}
    assert second["status"] == "DEMO_ALREADY_SEEDED"
    assert first["fingerprint"] == second["fingerprint"]
    assert first["counts"] == second["counts"]
    settings = get_settings()
    assert settings.database_url == os.environ["MARKET_PULSE_DEMO_DATABASE_URL"]
    with psycopg.connect(settings.database_url, connect_timeout=3) as connection:
        assert connection.execute("SELECT current_database()").fetchone()[0] == "market_pulse_demo"
        users = connection.execute(
            "SELECT id,email,password_hash FROM users ORDER BY email"
        ).fetchall()
        assert len(users) == 2
        assert all(row[2].startswith("$argon2id$") for row in users)
        assert all(verify_password(DEMO_LOCAL_PASSWORD, row[2]) for row in users)
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM price_bars WHERE data_level <> 'DEMO' OR data_level IS NULL"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM datasets WHERE status='PUBLIC_APPROVED'"
            ).fetchone()[0]
            == 0
        )
    service = PostgresPortfolioService(settings)
    for row, name, cash in zip(users, ("Alpha Demo", "Defensive Demo"), ("8020", "3185")):
        portfolio = service.list(str(row[0])).items[0]
        assert portfolio.name == name
        assert service.summary(str(row[0]), portfolio.id).cash_balances["BRL"] == Decimal(cash)
    assert len(PostgresEditorialService().list_published()) == 3


@pytest.mark.skipif(
    os.environ.get("MARKET_PULSE_DEMO_INTEGRATION") != "true",
    reason="Read-model validation requires the dedicated DEMO database",
)
def test_persisted_public_and_portfolio_reads_preserve_demo_integrity():
    import psycopg

    from app.contracts import HistoryPeriod, SeriesMode
    from app.demo.dataset import DEMO_CUTOFF
    from app.demo.operations import demo_settings
    from app.market_data.public_market_data import public_history, public_quote
    from app.portfolios.performance import PortfolioPerformanceService
    from app.portfolios.service import PostgresPortfolioService

    settings = demo_settings()
    quote = public_quote("demo.equity.mpxa3", "demo-gate")
    assert quote.price == Decimal("108")
    assert quote.data_level == "DEMO" and quote.freshness == "STALE"
    assert quote.timestamp_official == quote.timestamp_collected == DEMO_CUTOFF
    for period in HistoryPeriod:
        series = public_history("demo.equity.mpxa3", period, SeriesMode.INDEX_100, "demo-gate")
        assert len(series.points) >= 7
        assert series.points[0].index_100 == Decimal("100")
        assert series.points[-1].close == Decimal("108")
        assert series.data_level == "DEMO" and series.freshness == "STALE"
        assert series.timestamp_official == DEMO_CUTOFF
        assert series.tabular_fallback and series.limitations
    with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
        user_id = str(
            conn.execute("SELECT id FROM users WHERE email='demo.a@market-pulse.local'").fetchone()[
                0
            ]
        )
    portfolios = PostgresPortfolioService(settings)
    portfolio = portfolios.list(user_id).items[0]
    service = PortfolioPerformanceService(portfolios)
    valuation = service.valuation_response(user_id, portfolio.id)
    assert valuation.total_value_base == Decimal("10100")
    assert valuation.realized_pnl == Decimal("20")
    assert valuation.unrealized_pnl == Decimal("90")
    assert service.performance_response(user_id, portfolio.id).twr == Decimal("0.01")
    assert all(item.data_level == "DEMO" for item in valuation.provenance)


@pytest.mark.skipif(
    os.environ.get("MARKET_PULSE_DEMO_INTEGRATION") != "true",
    reason="License revocation gate operates only on local DEMO metadata",
)
def test_revoked_demo_dataset_is_unavailable_and_reset_rejects_it():
    import psycopg

    from app.demo.lifecycle import _verify_owned
    from app.demo.operations import demo_settings
    from app.demo.safety import DemoSafetyError
    from app.market_data.public_market_data import public_quote

    settings = demo_settings()
    with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
        _verify_owned(conn)
        try:
            conn.execute("UPDATE provider_dataset_licenses SET review_status='BLOCKED'")
            conn.commit()
            quote = public_quote("demo.equity.mpxa3", "demo-revocation-gate")
            assert quote.price is None and quote.freshness == "UNAVAILABLE"
            with pytest.raises(DemoSafetyError):
                _verify_owned(conn)
        finally:
            conn.execute("UPDATE provider_dataset_licenses SET review_status='DEMO_SYNTHETIC'")
            conn.commit()


@pytest.mark.skipif(
    os.environ.get("MARKET_PULSE_DEMO_INTEGRATION") != "true",
    reason="Dedicated DEMO database gate requires explicit opt-in",
)
def test_editorial_real_dict_rows_preserve_version_in_review_audit(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace
    from uuid import uuid4

    import psycopg
    from psycopg.rows import dict_row

    from app.core.config import get_settings
    from app.demo.safety import LOCAL_DEMO_CONFIRMATION, validate_demo_target
    from app.editorial.service import PostgresEditorialService
    from app.editorial.validator import EditorialBlock, EditorialStatus

    validate_demo_target(os.environ, confirmation=LOCAL_DEMO_CONFIRMATION)
    settings = get_settings()
    assert settings.database_url == os.environ["MARKET_PULSE_DEMO_DATABASE_URL"]
    connection = psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=3)
    assert connection.execute("SELECT current_database() AS name").fetchone()["name"] == (
        "market_pulse_demo"
    )

    @contextmanager
    def transaction_scoped_connection():
        # Execute real SQL and retain psycopg's real dict rows. Only transaction
        # completion is held by this test so rollback needs no immutable DELETE.
        yield SimpleNamespace(execute=connection.execute, commit=lambda: None)

    service = PostgresEditorialService()
    monkeypatch.setattr(service, "_connect", transaction_scoped_connection)
    try:
        post = service.create_draft(
            slug=f"demo-transition-{uuid4()}",
            title="DEMO — revisão",
            blocks=(EditorialBlock(content_type="LIMITATION", text="Cenário DEMO sintético."),),
        )
        transitioned = service.transition_by_id(post.id, EditorialStatus.UNDER_REVIEW)
        assert transitioned.status is EditorialStatus.UNDER_REVIEW
        row = connection.execute(
            "SELECT e.post_version_id,p.current_version_id FROM editorial_review_events e "
            "JOIN editorial_posts p ON p.id=e.post_id WHERE e.post_id=%s",
            (post.id,),
        ).fetchone()
        assert row["post_version_id"] is not None
        assert row["post_version_id"] == row["current_version_id"]
    finally:
        connection.rollback()
        connection.close()
