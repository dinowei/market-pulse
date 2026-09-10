"""Read the persisted synthetic scenario through existing public contracts.

No provider I/O, generated prices or approval of external data. Missing/revoked
datasets remain unavailable, including after a successful seed.
"""

from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

from app.contracts import HistoryPeriod, PublicHistoryPoint
from app.demo.dataset import DEMO_CUTOFF, DEMO_LIMITATIONS
from app.demo.operations import DEMO_DB_MARKER, demo_settings
from app.demo.safety import DemoSafetyError
from app.instruments.catalog import InstrumentCatalogEntry
from app.portfolios.performance import PriceMark
from app.providers.licensing import DatasetAccessRequest, LicenseService
from app.providers.models import DataLevel, ProviderCapability, ProviderDatasetRef


@contextmanager
def _connection(*, completed: bool = True):
    settings = demo_settings()
    with psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=3) as conn:
        identity = conn.execute(
            "SELECT current_database() AS name,shobj_description(oid,'pg_database') AS marker "
            "FROM pg_database WHERE datname=current_database()"
        ).fetchone()
        if not identity or identity != {"name": "market_pulse_demo", "marker": DEMO_DB_MARKER}:
            raise DemoSafetyError("DEMO database ownership is not verified")
        if (
            completed
            and not conn.execute(
                "SELECT 1 FROM audit_logs WHERE entity_type='demo_seed' "
                "AND action='demo_seed_completed'"
            ).fetchone()
        ):
            raise DemoSafetyError("DEMO initialization is not complete")
        yield conn


def catalog_entries() -> tuple[InstrumentCatalogEntry, ...]:
    # Metadata is needed by the existing watchlist/portfolio services during seed.
    with _connection(completed=False) as conn:
        rows = conn.execute(
            "SELECT i.*,e.code AS exchange,e.timezone,e.country, "
            "ARRAY(SELECT alias_symbol FROM instrument_aliases a WHERE a.instrument_id=i.id "
            "ORDER BY alias_symbol) AS aliases FROM instruments i "
            "JOIN exchanges e ON e.id=i.exchange_id WHERE e.code='DEMO' "
            "AND i.canonical_id LIKE 'demo.%' ORDER BY i.canonical_id"
        ).fetchall()
    return tuple(
        InstrumentCatalogEntry(
            canonical_id=row["canonical_id"],
            symbol=row["symbol"],
            display_symbol=row["symbol"],
            name=row["name"],
            instrument_type=row["instrument_type"],
            exchange=row["exchange"],
            venue=row["exchange"],
            country=row["country"],
            region="DEMO",
            currency=row["currency"],
            timezone=row["timezone"],
            aliases=tuple(row["aliases"]),
            catalog_status="ACTIVE",
            coverage_tier="P0_OPERATIONAL",
            data_support_status="PROVIDER_PENDING",
            notes=(
                "DEMO local persistido. Disponibilidade depende "
                "da licença sintética em cada leitura."
            ),
        )
        for row in rows
    )


def _allowed(row: dict, capability: ProviderCapability) -> bool:
    # This explicit scope belongs only to our local generator, never an external provider.
    settings = demo_settings()
    return (
        row["provider"] == "demo"
        and row["provider_status"] == "DEMO_SYNTHETIC"
        and row["dataset_status"] == "DEMO_SYNTHETIC"
        and row["data_level"] == "DEMO"
        and row["freshness"] in {"FRESH", "STALE"}
        and row["dataset"] in {"demo-day24-quotes", "demo-day24-bars-1d", "demo-day24-bars-1h"}
        and LicenseService()
        .decide_access(
            DatasetAccessRequest(
                dataset=ProviderDatasetRef(
                    provider=row["provider"],
                    dataset=row["dataset"],
                    license_status=row["review_status"],
                    evidence=bool(row["evidence_uri"]),
                    plan="internal-synthetic",
                    endpoint=capability.value,
                    purpose="local-demo",
                    modality="display",
                    environment=settings.environment,
                ),
                capability=capability,
                purpose="local-demo",
                modality="display",
                environment=settings.environment,
                data_level=DataLevel.DEMO,
            )
        )
        .allowed
    )


_JOINS = (
    " JOIN instruments i ON i.id=m.instrument_id JOIN providers p ON p.id=m.provider_id "
    "JOIN datasets d ON d.id=m.dataset_id AND d.provider_id=p.id "
    "JOIN provider_dataset_licenses l ON l.dataset_id=d.id AND l.provider_id=p.id "
)
_FIELDS = (
    "m.*,i.canonical_id,p.name AS provider,p.status AS provider_status,"
    "d.name AS dataset,d.status AS dataset_status,l.review_status,l.evidence_uri"
)


def quote_row(canonical_id: str) -> dict | None:
    with _connection() as conn:
        row = conn.execute(
            f"SELECT {_FIELDS} FROM quotes m {_JOINS} "
            "WHERE i.canonical_id=%s ORDER BY m.source_timestamp DESC LIMIT 1",
            (canonical_id,),
        ).fetchone()
    return row if row and _allowed(row, ProviderCapability.LATEST_QUOTE) else None


def bar_rows(canonical_id: str, period: HistoryPeriod = HistoryPeriod.MAX) -> list[dict]:
    days = {"1D": 1, "5D": 5, "1M": 30, "3M": 90, "6M": 180, "1A": 365, "5A": 1825}
    start = (
        date(DEMO_CUTOFF.year, 1, 1)
        if period == HistoryPeriod.YTD
        else DEMO_CUTOFF.date() - timedelta(days=days.get(period.value, 3650) - 1)
    )
    interval = "1h" if period.value in {"1D", "5D"} else "1d"
    with _connection() as conn:
        rows = conn.execute(
            f"SELECT {_FIELDS} FROM price_bars m {_JOINS} "
            "WHERE i.canonical_id=%s AND m.interval=%s AND m.adjustment_type='UNADJUSTED' "
            "AND m.source_timestamp BETWEEN %s AND %s ORDER BY m.source_timestamp",
            (canonical_id, interval, datetime.combine(start, time.min, timezone.utc), DEMO_CUTOFF),
        ).fetchall()
    # Do not draw across a rejected row. A partially revoked series is unavailable.
    if not all(_allowed(row, ProviderCapability.HISTORICAL_BARS) for row in rows):
        return []
    return rows


def history_points(rows: list[dict]) -> list[PublicHistoryPoint]:
    base = rows[0]["close"] if rows else None
    return [
        PublicHistoryPoint(
            timestamp=row["source_timestamp"],
            session_date=row["source_timestamp"].date(),
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            value=row["close"],
            index_100=row["close"] / base * Decimal("100") if base else None,
        )
        for row in rows
    ]


def price_marks(canonical_ids, as_of: date | None = None) -> dict[str, PriceMark]:
    marks = {}
    for canonical_id in set(canonical_ids):
        if not canonical_id:
            continue
        rows = [
            row
            for row in bar_rows(canonical_id)
            if as_of is None or row["source_timestamp"].date() == as_of
        ]
        if rows:
            row = rows[-1]
            marks[canonical_id] = PriceMark(
                canonical_id,
                row["close"],
                row["currency"],
                row["provider"],
                row["dataset"],
                row["data_level"],
                row["freshness"],
                row["source_timestamp"],
                row["collected_at"],
                DEMO_LIMITATIONS,
            )
    return marks
