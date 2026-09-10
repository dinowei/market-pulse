"""Authorized lifecycle of the disposable local DEMO database, never the primary DB."""

import hashlib
import json
import os
from pathlib import Path
from time import monotonic
from uuid import uuid4

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql
from redis import Redis

from app.demo.operations import (
    DEMO_CACHE_MARKER,
    DEMO_DB_MARKER,
    _log,
    _verify_database,
    demo_settings,
)
from app.demo.safety import DemoSafetyError

_OWNED_TABLES = frozenset(
    {
        "alembic_version",
        "audit_logs",
        "corporate_actions",
        "datasets",
        "editorial_blocks",
        "editorial_post_versions",
        "editorial_posts",
        "editorial_review_events",
        "editorial_sources",
        "exchanges",
        "instrument_aliases",
        "idempotency_keys",
        "instruments",
        "portfolio_cash_balances",
        "portfolio_events",
        "portfolio_positions",
        "portfolios",
        "price_bars",
        "provider_dataset_licenses",
        "providers",
        "quotes",
        "users",
        "watchlist_items",
        "watchlists",
    }
)
_LIFECYCLE_LOCK = 24012402


def _require_lifecycle_authorization() -> None:
    if os.environ.get("MARKET_PULSE_DEMO_ALLOW_RECREATE") != "true":
        raise DemoSafetyError("Explicit DEMO lifecycle authorization is required")


def _alembic_config() -> Config:
    api_root = Path(__file__).resolve().parents[2]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    return config


def _upgrade_to_head() -> None:
    command.upgrade(_alembic_config(), "head")


def _create_demo_database(admin) -> None:
    admin.execute("CREATE DATABASE market_pulse_demo")
    admin.execute("COMMENT ON DATABASE market_pulse_demo IS 'market-pulse-demo:v1'")


def bootstrap_demo() -> dict:
    """Create an absent dedicated DEMO database; never replace an existing database."""
    _require_lifecycle_authorization()
    settings = demo_settings()
    run_id, started = str(uuid4()), monotonic()
    _log("demo_bootstrap_started", run_id, started)
    try:
        with psycopg.connect(
            settings.database_url, dbname="postgres", autocommit=True, connect_timeout=3
        ) as admin:
            locked = admin.execute(
                "SELECT pg_try_advisory_lock(%s)", (_LIFECYCLE_LOCK,)
            ).fetchone()[0]
            if not locked:
                raise DemoSafetyError("Another DEMO lifecycle operation is running")
            if admin.execute(
                "SELECT 1 FROM pg_database WHERE datname='market_pulse_demo'"
            ).fetchone():
                raise DemoSafetyError("DEMO database already exists; bootstrap denied")
            _create_demo_database(admin)
        _upgrade_to_head()
        _log("demo_bootstrap_completed", run_id, started, database="market_pulse_demo")
        return {
            "status": "DEMO_BOOTSTRAPPED",
            "database": "market_pulse_demo",
            "migrations": "head",
            "primary_database_touched": False,
        }
    except Exception:
        _log("demo_bootstrap_failed", run_id, started, code="DEMO_BOOTSTRAP_FAILED")
        raise


def _verify_owned(connection) -> None:
    _verify_database(connection)
    marker = connection.execute(
        "SELECT shobj_description(oid,'pg_database') FROM pg_database "
        "WHERE datname=current_database()"
    ).fetchone()[0]
    if marker != DEMO_DB_MARKER:
        raise DemoSafetyError("DEMO ownership is not established; recreation denied")
    checks = (
        "SELECT 1 FROM exchanges WHERE code <> 'DEMO' OR country <> 'BR' "
        "OR timezone <> 'UTC' OR currency <> 'BRL'",
        "SELECT 1 FROM users WHERE email NOT IN "
        "('demo.a@market-pulse.local','demo.b@market-pulse.local')",
        "SELECT 1 FROM instruments WHERE canonical_id NOT LIKE 'demo.%' OR name NOT LIKE '%DEMO%'",
        "SELECT 1 FROM instrument_aliases a LEFT JOIN instruments i ON i.id=a.instrument_id "
        "WHERE i.canonical_id IS NULL OR i.canonical_id NOT LIKE 'demo.%' OR a.source <> 'DEMO'",
        "SELECT 1 FROM providers WHERE name <> 'demo' OR status <> 'DEMO_SYNTHETIC'",
        "SELECT 1 FROM datasets WHERE status <> 'DEMO_SYNTHETIC' OR name NOT LIKE 'demo-day24-%'",
        "SELECT 1 FROM provider_dataset_licenses l JOIN providers p ON p.id=l.provider_id "
        "JOIN datasets d ON d.id=l.dataset_id WHERE p.name <> 'demo' "
        "OR d.name NOT LIKE 'demo-day24-%' OR l.review_status <> 'DEMO_SYNTHETIC'",
        "SELECT 1 FROM quotes q JOIN instruments i ON i.id=q.instrument_id "
        "JOIN providers p ON p.id=q.provider_id JOIN datasets d ON d.id=q.dataset_id "
        "WHERE i.canonical_id NOT LIKE 'demo.%' OR p.name <> 'demo' "
        "OR d.name NOT LIKE 'demo-day24-%' OR q.data_level IS DISTINCT FROM 'DEMO'",
        "SELECT 1 FROM price_bars b JOIN instruments i ON i.id=b.instrument_id "
        "JOIN providers p ON p.id=b.provider_id JOIN datasets d ON d.id=b.dataset_id "
        "WHERE i.canonical_id NOT LIKE 'demo.%' OR p.name <> 'demo' "
        "OR d.name NOT LIKE 'demo-day24-%' OR b.data_level IS DISTINCT FROM 'DEMO'",
        "SELECT 1 FROM corporate_actions a JOIN instruments i ON i.id=a.instrument_id "
        "JOIN providers p ON p.id=a.provider_id JOIN datasets d ON d.id=a.dataset_id "
        "WHERE i.canonical_id NOT LIKE 'demo.%' OR p.name <> 'demo' "
        "OR d.name NOT LIKE 'demo-day24-%'",
        "SELECT 1 FROM portfolios p JOIN users u ON u.id=p.user_id "
        "WHERE u.email NOT IN ('demo.a@market-pulse.local','demo.b@market-pulse.local')",
        "SELECT 1 FROM portfolio_positions pp JOIN portfolios p ON p.id=pp.portfolio_id "
        "JOIN users u ON u.id=p.user_id WHERE u.email NOT IN "
        "('demo.a@market-pulse.local','demo.b@market-pulse.local')",
        "SELECT 1 FROM portfolio_cash_balances cb JOIN portfolios p ON p.id=cb.portfolio_id "
        "JOIN users u ON u.id=p.user_id WHERE u.email NOT IN "
        "('demo.a@market-pulse.local','demo.b@market-pulse.local')",
        "SELECT 1 FROM portfolio_events e JOIN portfolios p ON p.id=e.portfolio_id "
        "JOIN users u ON u.id=p.user_id WHERE u.email NOT IN "
        "('demo.a@market-pulse.local','demo.b@market-pulse.local') "
        "OR e.note NOT LIKE 'DEMO:%' OR e.note IS NULL "
        "OR e.idempotency_key NOT LIKE 'demo-day24:%' OR e.idempotency_key IS NULL",
        "SELECT 1 FROM watchlists w JOIN users u ON u.id=w.user_id WHERE u.email NOT IN "
        "('demo.a@market-pulse.local','demo.b@market-pulse.local')",
        "SELECT 1 FROM watchlist_items wi JOIN watchlists w ON w.id=wi.watchlist_id "
        "JOIN users u ON u.id=w.user_id JOIN instruments i ON i.id=wi.instrument_id "
        "WHERE u.email NOT IN ('demo.a@market-pulse.local','demo.b@market-pulse.local') "
        "OR i.canonical_id NOT LIKE 'demo.%'",
        "SELECT 1 FROM editorial_posts WHERE slug NOT LIKE 'demo-morning-call-%' "
        "OR title NOT LIKE '%DEMO%'",
        "SELECT 1 FROM editorial_post_versions WHERE title NOT LIKE '%DEMO%'",
        "SELECT 1 FROM idempotency_keys WHERE method <> 'POST' "
        "OR path <> '/api/v1/portfolio-events' "
        "OR (response_json - 'status' - 'idempotency_key') <> '{}'::jsonb",
    )
    if any(connection.execute(query + " LIMIT 1").fetchone() for query in checks):
        raise DemoSafetyError("Unrecognized or non-DEMO content; recreation denied")
    tables = connection.execute(
        "SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN "
        "('pg_catalog','information_schema') AND schemaname NOT LIKE 'pg_toast%'"
    ).fetchall()
    for schema, table in tables:
        if schema != "public" or table not in _OWNED_TABLES:
            if connection.execute(
                sql.SQL("SELECT 1 FROM {}.{} LIMIT 1").format(
                    sql.Identifier(schema),
                    sql.Identifier(table),
                )
            ).fetchone():
                raise DemoSafetyError("Unrecognized populated table; recreation denied")


def _cache_for_reset(settings):
    cache = Redis.from_url(
        settings.redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
    )
    if cache.get(DEMO_CACHE_MARKER) != DEMO_DB_MARKER:
        cache.close()
        raise DemoSafetyError("DEMO cache ownership rejected")
    keys = list(cache.scan_iter())
    allowed = ("auth:session:", "auth:register:ip:", "auth:login:ip:")
    if any(key != DEMO_CACHE_MARKER and not key.startswith(allowed) for key in keys):
        cache.close()
        raise DemoSafetyError("Unrecognized DEMO cache entry; recreation denied")
    return cache, [key for key in keys if key != DEMO_CACHE_MARKER]


def reset_demo() -> dict:
    # Separate human-enabled flag in addition to APP_ENV, host, exact name and
    # the internal confirmation checked by demo_settings/validate_demo_target.
    _require_lifecycle_authorization()
    settings = demo_settings()
    run_id, started = str(uuid4()), monotonic()
    _log("demo_reset_started", run_id, started)
    cache = None
    try:
        check = psycopg.connect(settings.database_url, connect_timeout=3)
        _verify_owned(check)
        check_pid = check.execute("SELECT pg_backend_pid()").fetchone()[0]
        cache, keys = _cache_for_reset(settings)
        # Maintenance connection is to postgres, never market_pulse. The DSN was
        # fully guarded first and dbname is a fixed keyword override, not user SQL.
        with psycopg.connect(
            settings.database_url, dbname="postgres", autocommit=True, connect_timeout=3
        ) as admin:
            locked = admin.execute(
                "SELECT pg_try_advisory_lock(%s)", (_LIFECYCLE_LOCK,)
            ).fetchone()[0]
            if not locked:
                raise DemoSafetyError("Another DEMO lifecycle operation is running")
            row = admin.execute(
                "SELECT shobj_description(oid,'pg_database'),datallowconn "
                "FROM pg_database WHERE datname='market_pulse_demo'"
            ).fetchone()
            if row != (DEMO_DB_MARKER, True):
                raise DemoSafetyError("DEMO live identity changed; recreation denied")
            # Do not kill sessions. Stop API/worker before reset. Blocking new
            # connections closes the race between the active-session check and DROP.
            admin.execute("ALTER DATABASE market_pulse_demo ALLOW_CONNECTIONS false")
            dropped = False
            try:
                if admin.execute(
                    "SELECT 1 FROM pg_stat_activity WHERE datname='market_pulse_demo' "
                    "AND pid <> %s LIMIT 1",
                    (check_pid,),
                ).fetchone():
                    raise DemoSafetyError("Stop DEMO API/worker connections before reset")
                _verify_owned(check)  # recheck with new connections blocked and no other sessions
                check.close()
                admin.execute("DROP DATABASE market_pulse_demo")
                dropped = True
                _create_demo_database(admin)
            finally:
                if not dropped:
                    admin.execute("ALTER DATABASE market_pulse_demo ALLOW_CONNECTIONS true")
        # Never DELETE/TRUNCATE immutable rows or alter triggers. Recreate the
        # disposable database, then use the exact existing Alembic migrations.
        _upgrade_to_head()
        if keys:
            cache.delete(*keys)
        _log("demo_reset_completed", run_id, started, database="market_pulse_demo")
        return {
            "status": "DEMO_RESET",
            "database": "market_pulse_demo",
            "migrations": "head",
            "cache_entries_invalidated": len(keys),
            "primary_database_touched": False,
        }
    except Exception:
        _log("demo_reset_failed", run_id, started, code="DEMO_RESET_FAILED")
        raise
    finally:
        if "check" in locals():
            check.close()
        if cache is not None:
            cache.close()


def logical_snapshot() -> str:
    """Hash persisted semantic content, not generated IDs, salts or audit-clock times."""
    settings = demo_settings()
    queries = (
        "SELECT email,status,role,password_hash LIKE '$argon2id$%' FROM users ORDER BY email",
        "SELECT canonical_id,symbol,name,instrument_type,currency,status FROM instruments "
        "ORDER BY canonical_id",
        "SELECT p.name,d.name,d.status,l.review_status FROM datasets d JOIN providers p "
        "ON p.id=d.provider_id JOIN provider_dataset_licenses l ON l.dataset_id=d.id "
        "ORDER BY d.name",
        "SELECT i.canonical_id,q.price,q.currency,q.data_level,q.freshness,q.source_timestamp,"
        "q.collected_at,q.source FROM quotes q JOIN instruments i ON i.id=q.instrument_id "
        "ORDER BY i.canonical_id,q.source_timestamp",
        "SELECT i.canonical_id,b.interval,b.open,b.high,b.low,b.close,b.volume,b.currency,"
        "b.source_timestamp,b.collected_at,b.data_level,b.freshness,b.adjustment_type "
        "FROM price_bars b JOIN instruments i ON i.id=b.instrument_id "
        "ORDER BY i.canonical_id,b.interval,b.source_timestamp",
        "SELECT i.canonical_id,a.action_type,a.status,a.external_event_key,"
        "a.ex_date,a.payment_date,"
        "a.effective_date,a.currency,a.gross_amount_per_share,a.net_amount_per_share,"
        "a.split_ratio_from,a.split_ratio_to FROM corporate_actions a "
        "JOIN instruments i ON i.id=a.instrument_id ORDER BY i.canonical_id,a.external_event_key",
        "SELECT u.email,w.name,w.is_system,i.canonical_id,wi.position FROM watchlists w "
        "JOIN users u ON u.id=w.user_id LEFT JOIN watchlist_items wi ON wi.watchlist_id=w.id "
        "LEFT JOIN instruments i ON i.id=wi.instrument_id ORDER BY u.email,w.name,wi.position",
        "SELECT u.email,p.name,p.base_currency,e.event_type,i.canonical_id,e.occurred_at,"
        "e.quantity,e.price,e.gross_amount,e.fees,e.currency,e.note,e.idempotency_key,"
        "r.idempotency_key FROM portfolios p JOIN users u ON u.id=p.user_id "
        "LEFT JOIN portfolio_events e ON e.portfolio_id=p.id "
        "LEFT JOIN instruments i ON i.id=e.instrument_id "
        "LEFT JOIN portfolio_events r ON r.id=e.reversed_event_id "
        "ORDER BY u.email,p.name,e.occurred_at,e.idempotency_key",
        "SELECT p.slug,p.title,p.summary,p.content_date,p.status,v.version_number,v.blocks,"
        "v.status_snapshot FROM editorial_posts p JOIN editorial_post_versions v ON v.post_id=p.id "
        "ORDER BY p.slug,v.version_number",
    )
    with psycopg.connect(settings.database_url, connect_timeout=3) as connection:
        _verify_owned(connection)
        contents = [connection.execute(query).fetchall() for query in queries]
    encoded = json.dumps(contents, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
