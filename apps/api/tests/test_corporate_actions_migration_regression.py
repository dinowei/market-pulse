"""Opt-in real-Postgres regression for the populated corporate-actions rollback."""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config

from app.core.config import get_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("MARKET_PULSE_MIGRATION_REGRESSION") != "true",
    reason="requires an explicitly dedicated local/CI migration regression database",
)


def _migration_database_url() -> str:
    url = os.environ.get("MARKET_PULSE_MIGRATION_DATABASE_URL", "")
    if "market_pulse_migration_test" not in url or "127.0.0.1" not in url:
        raise AssertionError(
            "MARKET_PULSE_MIGRATION_DATABASE_URL must target local market_pulse_migration_test"
        )
    return url


def _alembic() -> Config:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    return config


def test_populated_corporate_actions_rollback_is_lossless() -> None:
    url = _migration_database_url()
    previous = os.environ.get("MARKET_PULSE_DATABASE_URL")
    os.environ["MARKET_PULSE_DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        command.upgrade(_alembic(), "20260901_0003")
        command.upgrade(_alembic(), "20260902_0004")
        action_id, instrument_id, provider_id, exchange_id = (str(uuid4()) for _ in range(4))
        suffix = action_id.replace("-", "")[:10]
        exchange_code = f"M{suffix[:3]}"
        instrument_symbol = f"MIG{suffix[:4]}"
        provider_name = f"migration-demo-{suffix}"
        with psycopg.connect(url) as connection:
            connection.execute(
                "INSERT INTO exchanges (id,code,name,country,timezone,currency) "
                "VALUES (%s,%s,'Migration Test','BR','UTC','BRL')",
                (exchange_id, exchange_code),
            )
            connection.execute(
                "INSERT INTO instruments (id,exchange_id,symbol,name,instrument_type,currency) "
                "VALUES (%s,%s,%s,'Migration Test DEMO','EQUITY','BRL')",
                (instrument_id, exchange_id, instrument_symbol),
            )
            connection.execute(
                "INSERT INTO providers (id,name,status) VALUES (%s,%s,'DEMO_SYNTHETIC')",
                (provider_id, provider_name),
            )
            row = connection.execute(
                "INSERT INTO corporate_actions "
                "(id,instrument_id,provider_id,action_type,effective_date,declared_date,"
                "amount,currency,ratio,source_timestamp,external_event_key) "
                "VALUES (%s,%s,%s,'CASH_DIVIDEND',NULL,NULL,%s,'BRL',NULL,NULL,%s) "
                "RETURNING created_at::date",
                (action_id, instrument_id, provider_id, "1.25", f"legacy:{action_id}"),
            ).fetchone()
            created_date = row[0]
            connection.commit()

        command.upgrade(_alembic(), "head")
        with psycopg.connect(url) as connection:
            before = connection.execute(
                "SELECT effective_date, source_timestamp FROM corporate_actions WHERE id=%s",
                (action_id,),
            ).fetchone()
            assert before == (None, None)

        command.downgrade(_alembic(), "20260901_0003")
        with psycopg.connect(url) as connection:
            after = connection.execute(
                "SELECT effective_date, source_timestamp, amount "
                "FROM corporate_actions WHERE id=%s",
                (action_id,),
            ).fetchone()
            assert after is not None
            assert after[0] == created_date
            assert after[1] is not None
            assert after[2] == Decimal("1.25")

        command.upgrade(_alembic(), "head")
        with psycopg.connect(url) as connection:
            final = connection.execute(
                "SELECT effective_date, source_timestamp FROM corporate_actions WHERE id=%s",
                (action_id,),
            ).fetchone()
            assert final is not None
            assert final[0] == created_date
            assert final[1] is not None
    finally:
        if previous is None:
            os.environ.pop("MARKET_PULSE_DATABASE_URL", None)
        else:
            os.environ["MARKET_PULSE_DATABASE_URL"] = previous
        get_settings.cache_clear()
