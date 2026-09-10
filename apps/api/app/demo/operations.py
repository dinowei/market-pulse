"""Administrative seeding through the existing domains, restricted to local DEMO."""

from __future__ import annotations

import json
import os
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit
from uuid import uuid4, uuid5

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from redis import Redis

from app.auth.service import AuthService
from app.contracts import PortfolioCreateRequest, PortfolioEventRequest, RegisterRequest
from app.core.config import get_settings
from app.demo.dataset import DEMO_NAMESPACE, DemoDataset, build_demo_dataset
from app.demo.safety import (
    LOCAL_DEMO_CONFIRMATION,
    DemoSafetyError,
    validate_demo_target,
)
from app.editorial.service import PostgresEditorialService
from app.editorial.validator import EditorialStatus
from app.portfolios.performance import PriceMark, calculate_valuation
from app.portfolios.service import PostgresPortfolioService
from app.watchlists.service import PostgresWatchlistService

# Explicitly fictional, local-only demonstration credential authorized by the operator.
DEMO_LOCAL_PASSWORD = "MarketPulseDemo2026!"
DEMO_DB_MARKER = "market-pulse-demo:v1"
_SEED_LOCK = 24012401
DEMO_CACHE_MARKER = "market-pulse:demo:owner"


def reset_demo() -> dict:
    from app.demo.lifecycle import reset_demo as reset

    return reset()


def bootstrap_demo() -> dict:
    from app.demo.lifecycle import bootstrap_demo as bootstrap

    return bootstrap()


def logical_snapshot() -> str:
    from app.demo.lifecycle import logical_snapshot as snapshot

    return snapshot()


def demo_settings():
    validate_demo_target(os.environ, confirmation=LOCAL_DEMO_CONFIRMATION)
    settings = get_settings()
    if not settings.demo_enabled or settings.database_url != os.environ.get(
        "MARKET_PULSE_DEMO_DATABASE_URL"
    ):
        raise DemoSafetyError("The running application must explicitly target the DEMO database")
    try:
        cache = urlsplit(settings.redis_url)
        valid = (
            cache.scheme == "redis"
            and cache.hostname in {"localhost", "127.0.0.1", "::1"}
            and cache.path == "/15"
            and not cache.query
            and not cache.fragment
        )
    except ValueError:
        valid = False
    if not valid:
        raise DemoSafetyError("DEMO requires its dedicated local Redis database 15")
    return settings


def _id(key: str) -> str:
    return str(uuid5(DEMO_NAMESPACE, key))


def _prepare_cache(settings) -> None:
    cache = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    try:
        owner = cache.get(DEMO_CACHE_MARKER)
        if owner == DEMO_DB_MARKER:
            return
        if owner is not None or cache.dbsize() != 0:
            raise DemoSafetyError("Unrecognized content in the dedicated DEMO cache")
        if not cache.set(DEMO_CACHE_MARKER, DEMO_DB_MARKER, nx=True):
            raise DemoSafetyError("DEMO cache initialization conflict")
    finally:
        cache.close()


def _log(event: str, run_id: str, started: float, **safe_fields) -> None:
    import sys

    print(
        json.dumps(
            {
                "event": event,
                "run_id": run_id,
                "environment": "local-demo",
                "duration_ms": int((monotonic() - started) * 1000),
                **safe_fields,
            }
        ),
        file=sys.stderr,
    )


def _verify_database(connection) -> None:
    row = connection.execute(
        "SELECT current_database(), shobj_description(oid,'pg_database') "
        "FROM pg_database WHERE datname=current_database()"
    ).fetchone()
    if row is None or row[0] != "market_pulse_demo":
        raise DemoSafetyError("DEMO server identity rejected")
    if row[1] not in {None, DEMO_DB_MARKER}:
        raise DemoSafetyError("DEMO ownership marker rejected")
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    api_root = Path(__file__).resolve().parents[2]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    if not revision or revision[0] != ScriptDirectory.from_config(config).get_current_head():
        raise DemoSafetyError("DEMO migrations must be at head")


def _assert_seed_database_empty(connection) -> None:
    """Refuse every pre-existing public row, except Alembic's schema revision."""
    tables = connection.execute(
        "SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN "
        "('pg_catalog','information_schema') AND schemaname NOT LIKE 'pg_toast%'"
    ).fetchall()
    for schema, table in tables:
        if schema == "public" and table == "alembic_version":
            continue
        if connection.execute(
            sql.SQL("SELECT 1 FROM {}.{} LIMIT 1").format(
                sql.Identifier(schema),
                sql.Identifier(table),
            )
        ).fetchone():
            raise DemoSafetyError("Unrecognized database content; refusing to seed")


def _market_data(connection, scenario: DemoDataset) -> None:
    cutoff = scenario.cutoff
    exchange_id, provider_id = _id("exchange"), _id("provider")
    connection.execute(
        "INSERT INTO exchanges (id,code,name,country,timezone,currency,created_at) "
        "VALUES (%s,'DEMO','Mercado fictício DEMO','BR','UTC','BRL',%s)",
        (exchange_id, cutoff),
    )
    connection.execute(
        "INSERT INTO providers (id,name,status,created_at) VALUES (%s,'demo','DEMO_SYNTHETIC',%s)",
        (provider_id, cutoff),
    )
    dataset_names = {
        item.provenance.dataset
        for item in (*scenario.daily_bars, *scenario.intraday_bars, *scenario.corporate_actions)
    } | {"demo-day24-quotes"}
    for name in sorted(dataset_names):
        dataset_id = _id(f"dataset:{name}")
        connection.execute(
            "INSERT INTO datasets (id,provider_id,name,status,purpose,created_at) "
            "VALUES (%s,%s,%s,'DEMO_SYNTHETIC','local-demo',%s)",
            (dataset_id, provider_id, name, cutoff),
        )
        connection.execute(
            "INSERT INTO provider_dataset_licenses "
            "(provider_id,dataset_id,review_status,evidence_uri,reviewed_at) "
            "VALUES (%s,%s,'DEMO_SYNTHETIC',%s,%s)",
            (provider_id, dataset_id, "docs/demo/DEMO_SEED_DAY_24.md", cutoff),
        )
    for entry in scenario.instruments:
        instrument_id = _id(f"instrument:{entry.canonical_id}")
        connection.execute(
            "INSERT INTO instruments "
            "(id,exchange_id,canonical_id,symbol,name,instrument_type,currency,status,"
            "created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,'ACTIVE',%s,%s)",
            (
                instrument_id,
                exchange_id,
                entry.canonical_id,
                entry.symbol,
                entry.name,
                entry.instrument_type,
                entry.currency,
                cutoff,
                cutoff,
            ),
        )
        for alias in (entry.symbol, *entry.aliases):
            connection.execute(
                "INSERT INTO instrument_aliases (instrument_id,alias_symbol,source,created_at) "
                "VALUES (%s,%s,'DEMO',%s)",
                (instrument_id, alias, cutoff),
            )
    bars = []
    latest = {}
    for item in (*scenario.daily_bars, *scenario.intraday_bars):
        bar, provenance = item.bar, item.provenance
        bars.append(
            (
                item.id,
                _id(f"instrument:{bar.canonical_id}"),
                provider_id,
                _id(f"dataset:{provenance.dataset}"),
                item.interval,
                bar.open,
                bar.high,
                bar.low,
                bar.close,
                bar.volume,
                bar.currency,
                bar.timestamp,
                provenance.collected_at,
                provenance.source,
                provenance.data_level.value,
                provenance.freshness.value,
                bar.adjustment_type.value,
            )
        )
        if item.interval == "1d":
            latest[bar.canonical_id] = item
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO price_bars (id,instrument_id,provider_id,dataset_id,interval,"
            "open,high,low,close,volume,currency,source_timestamp,collected_at,source,"
            "data_level,freshness,adjustment_type) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            bars,
        )
    for canonical_id, item in latest.items():
        connection.execute(
            "INSERT INTO quotes (instrument_id,provider_id,dataset_id,price,currency,"
            "data_level,freshness,source_timestamp,collected_at,source) "
            "VALUES (%s,%s,%s,%s,%s,'DEMO','STALE',%s,%s,%s)",
            (
                _id(f"instrument:{canonical_id}"),
                provider_id,
                _id("dataset:demo-day24-quotes"),
                item.bar.close,
                item.bar.currency,
                item.bar.timestamp,
                item.provenance.collected_at,
                item.provenance.source,
            ),
        )
    for item in scenario.corporate_actions:
        event = item.action
        connection.execute(
            "INSERT INTO corporate_actions "
            "(id,instrument_id,provider_id,dataset_id,action_type,status,external_id,"
            "external_event_key,announced_date,ex_date,record_date,payment_date,effective_date,"
            "currency,gross_amount_per_share,net_amount_per_share,withholding_tax_rate,"
            "split_ratio_from,split_ratio_to,source_timestamp,collected_at,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                event.event_id,
                _id(f"instrument:{event.instrument_id}"),
                provider_id,
                _id(f"dataset:{event.dataset}"),
                event.action_type.value,
                event.status.value,
                event.external_id,
                event.external_event_key,
                event.announced_date,
                event.ex_date,
                event.record_date,
                event.payment_date,
                event.effective_date,
                event.currency,
                event.gross_amount_per_share,
                event.net_amount_per_share,
                event.withholding_tax_rate,
                event.split_ratio_from,
                event.split_ratio_to,
                event.source_timestamp,
                event.collected_at,
                event.created_at,
                event.updated_at,
            ),
        )


def _private_resources(settings, scenario: DemoDataset) -> dict[str, str]:
    auth = AuthService(settings=settings)
    watchlists = PostgresWatchlistService(settings)
    portfolios = PostgresPortfolioService(settings)
    users = {}
    for user in scenario.users:
        created = auth.register(
            RegisterRequest(email=user.email, password=DEMO_LOCAL_PASSWORD), "demo-seed-local"
        )
        users[user.owner_key] = created.id
    for item in scenario.watchlists:
        owner = users[item.owner_key]
        created = watchlists.create(owner, item.name)
        for canonical_id in item.canonical_ids:
            watchlists.add_item(owner, created.id, canonical_id)
    for item in scenario.favorites:
        watchlists.favorite(users[item.owner_key], item.canonical_id)
    for item in scenario.portfolios:
        owner = users[item.owner_key]
        created = portfolios.create(
            owner, PortfolioCreateRequest(name=item.name, base_currency=item.base_currency)
        )
        event_ids = {}
        for event in item.events:
            payload = PortfolioEventRequest(
                event_type=event.event_type,
                currency=event.currency,
                canonical_id=event.canonical_id,
                quantity=event.quantity,
                unit_price=event.unit_price,
                gross_amount=event.gross_amount,
                fee_amount=event.fee_amount,
                occurred_at=event.occurred_at,
                notes=event.notes,
                reversal_of_event_id=event_ids.get(event.reversal_of_event_id),
            )
            persisted = portfolios.add_event(
                owner, created.id, payload, event.idempotency_key, "demo-seed-local"
            )
            event_ids[event.id] = persisted.id
        portfolios.summary(owner, created.id)
    return users


def _editorial(scenario: DemoDataset, actor: str) -> None:
    service = PostgresEditorialService()
    for item in scenario.editorial_drafts:
        draft = service.create_draft(
            **item.request.model_dump(exclude={"blocks"}),
            blocks=item.request.blocks,
            created_by_user_id=actor,
        )
        for target in (
            EditorialStatus.UNDER_REVIEW,
            EditorialStatus.APPROVED,
            EditorialStatus.PUBLISHED,
        ):
            service.transition_by_id(
                draft.id,
                target,
                actor_user_id=actor,
                reason="Publicação administrativa do cenário sintético DEMO autorizado.",
                request_id="demo-seed-local",
            )


def _verify_seed(connection, settings, scenario: DemoDataset, users: dict[str, str]) -> dict:
    rows = connection.execute(
        "SELECT i.canonical_id,q.price,q.currency,p.name,d.name,q.data_level,q.freshness,"
        "q.source_timestamp,q.collected_at FROM quotes q "
        "JOIN instruments i ON i.id=q.instrument_id JOIN providers p ON p.id=q.provider_id "
        "JOIN datasets d ON d.id=q.dataset_id"
    ).fetchall()
    if len(rows) != len(scenario.instruments) or any(row[5] != "DEMO" for row in rows):
        raise DemoSafetyError("DEMO quote integrity failed")
    prices = {row[0]: PriceMark(*row) for row in rows}
    portfolios = PostgresPortfolioService(settings)
    for planned in scenario.portfolios:
        owner = users[planned.owner_key]
        matches = [item for item in portfolios.list(owner).items if item.name == planned.name]
        if len(matches) != 1:
            raise DemoSafetyError("DEMO portfolio integrity failed")
        summary = portfolios.summary(owner, matches[0].id)
        # Read the real persisted ledger through the existing service, not a second replay.
        from app.portfolios.performance import event_inputs

        valuation = calculate_valuation(
            event_inputs(portfolios.events(owner, matches[0].id)),
            base_currency=planned.base_currency,
            prices=prices,
            fx_rates={},
        )
        if (
            valuation.status != "COMPLETE"
            or summary.event_count != len(planned.events)
            or summary.cash_balances != valuation.cash_balances
            or any(value < 0 for value in summary.cash_balances.values())
        ):
            raise DemoSafetyError("DEMO financial integrity failed")
    published = PostgresEditorialService().list_published()
    if len(published) != len(scenario.editorial_drafts):
        raise DemoSafetyError("DEMO publication integrity failed")
    return {"financial_replay": "PASS", "published_posts": len(published)}


def seed_demo() -> dict:
    settings = demo_settings()
    scenario = build_demo_dataset()
    run_id, started = str(uuid4()), monotonic()
    _log("demo_seed_started", run_id, started)
    try:
        with psycopg.connect(settings.database_url, connect_timeout=3) as connection:
            _verify_database(connection)
            locked = connection.execute("SELECT pg_try_advisory_lock(%s)", (_SEED_LOCK,)).fetchone()
            if not locked[0]:
                raise DemoSafetyError("Another DEMO administrative operation is running")
            marker = connection.execute(
                "SELECT action,metadata FROM audit_logs WHERE entity_type='demo_seed' "
                "ORDER BY occurred_at DESC LIMIT 1"
            ).fetchone()
            if marker:
                if marker[0] != "demo_seed_completed":
                    raise DemoSafetyError(
                        "DEMO initialization is incomplete; verified reset required"
                    )
                report = marker[1]
                if report["fingerprint"] != scenario.fingerprint():
                    raise DemoSafetyError("DEMO scenario changed; verified reset required")
                _log("demo_seed_completed", run_id, started, status="DEMO_ALREADY_SEEDED")
                return {**report, "status": "DEMO_ALREADY_SEEDED"}
            _assert_seed_database_empty(connection)
            _prepare_cache(settings)
            connection.execute("COMMENT ON DATABASE market_pulse_demo IS 'market-pulse-demo:v1'")
            connection.execute(
                "INSERT INTO audit_logs (entity_type,action,metadata) VALUES "
                "('demo_seed','demo_seed_started',%s)",
                (Jsonb({"run_id": run_id}),),
            )
            _market_data(connection, scenario)
            connection.commit()
            users = _private_resources(settings, scenario)
            _editorial(scenario, users["A"])
            integrity = _verify_seed(connection, settings, scenario, users)
            summary = scenario.summary()
            report = {
                "status": "DEMO_SEEDED",
                "fingerprint": scenario.fingerprint(),
                "data_level": "DEMO",
                "external_providers": "DISABLED",
                "integrity": integrity,
                "counts": {key: value for key, value in summary.items() if isinstance(value, int)},
            }
            connection.execute(
                "INSERT INTO audit_logs (entity_type,action,metadata) VALUES "
                "('demo_seed','demo_seed_completed',%s)",
                (Jsonb(report),),
            )
            connection.commit()
        _log("demo_seed_completed", run_id, started, counts=report["counts"])
        return report
    except Exception:
        _log("demo_seed_failed", run_id, started, code="DEMO_SEED_FAILED")
        raise
