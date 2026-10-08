from __future__ import annotations

import re
import time
from datetime import datetime, timezone

import psycopg
from redis import Redis

from app.contracts import (
    AdminBackfillStatus,
    AdminBackgroundJobsStatus,
    AdminContractStatus,
    AdminEditorialConsumptionStatus,
    AdminHealthStatus,
    AdminLocksStatus,
    AdminLockStatus,
    AdminProviderGovernanceStatus,
    AdminProviderStatus,
    AdminQuarantineStatus,
    AdminStructuredError,
    AdminSystemResponse,
    AdminVolumetricStatus,
)
from app.core.config import get_settings

_SECRET_RE = re.compile(
    r"(?i)(?:password|token|secret|api[_-]?key|authorization|cookie)\s*[:=]\s*[^\s,;]+"
)
_URL_RE = re.compile(r"(?i)(?:postgres(?:ql)?|redis|https?)://[^\s]+")
_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|/)[^\s]+")


def sanitize_admin_message(message: str) -> str:
    """Return a short diagnostic without credentials, URLs, or local paths."""
    value = _SECRET_RE.sub("[redacted]", str(message))
    value = _URL_RE.sub("[endpoint redacted]", value)
    value = _PATH_RE.sub("[path redacted]", value)
    return value[:240]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _db_rows(query: str, params: tuple[object, ...] = ()) -> list[tuple]:
    settings = get_settings()
    with psycopg.connect(
        settings.database_url,
        connect_timeout=max(1, int(settings.database_timeout_seconds)),
    ) as connection:
        return list(connection.execute(query, params).fetchall())


def _postgres_status(checked_at: datetime) -> AdminHealthStatus:
    started = time.perf_counter()
    try:
        _db_rows("SELECT 1")
        return AdminHealthStatus(
            status="ok",
            latency_ms=max(0, int((time.perf_counter() - started) * 1000)),
            checked_at=checked_at,
        )
    except Exception:
        return AdminHealthStatus(
            status="down", latency_ms=None, checked_at=checked_at
        )


def _redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.cache_timeout_seconds,
        socket_timeout=settings.cache_timeout_seconds,
        decode_responses=True,
    )


def _redis_status(checked_at: datetime) -> AdminHealthStatus:
    started = time.perf_counter()
    try:
        _redis_client().ping()
        return AdminHealthStatus(
            status="ok",
            latency_ms=max(0, int((time.perf_counter() - started) * 1000)),
            checked_at=checked_at,
        )
    except Exception:
        return AdminHealthStatus(status="down", latency_ms=None, checked_at=checked_at)


def _background_jobs(checked_at: datetime) -> AdminBackgroundJobsStatus:
    try:
        latest = _db_rows(
            "SELECT started_at, finished_at, status, job_id FROM ingestion_runs "
            "ORDER BY started_at DESC LIMIT 1"
        )
        backfills = _db_rows(
            "SELECT status, started_at, job_id FROM ingestion_runs "
            "WHERE capability ILIKE %s ORDER BY started_at DESC LIMIT 5",
            ("%backfill%",),
        )
        errors = _db_rows(
            "SELECT error_code, error_message, started_at FROM ingestion_runs "
            "WHERE error_code IS NOT NULL ORDER BY started_at DESC LIMIT 5"
        )
    except Exception:
        latest, backfills, errors = [], [], []
    last_refresh = latest[0][1] or latest[0][0] if latest else None
    return AdminBackgroundJobsStatus(
        last_refresh_at=last_refresh,
        backfills=[
            AdminBackfillStatus(
                status=str(row[0]),
                occurred_at=row[1],
                job_id=str(row[2]) if row[2] else None,
            )
            for row in backfills
        ],
        errors=[
            AdminStructuredError(
                code=str(row[0]), message=sanitize_admin_message(row[1] or ""), occurred_at=row[2]
            )
            for row in errors
        ],
        checked_at=checked_at,
    )


def _providers(checked_at: datetime) -> AdminProviderGovernanceStatus:
    try:
        rows = _db_rows(
            "SELECT p.name, d.name, p.status, d.status, l.review_status "
            "FROM providers p JOIN datasets d ON d.provider_id=p.id "
            "LEFT JOIN provider_dataset_licenses l ON l.provider_id=p.id AND l.dataset_id=d.id "
            "ORDER BY p.name, d.name LIMIT 100"
        )
    except Exception:
        rows = []
    items = []
    for provider, dataset, provider_status, dataset_status, license_status in rows:
        provider_status = str(provider_status)
        dataset_status = str(dataset_status)
        license_status = str(license_status or "DENIED")
        items.append(
            AdminProviderStatus(
                provider=str(provider),
                dataset=str(dataset),
                provider_status=provider_status,
                dataset_status=dataset_status,
                license_status=license_status,
                access="allowed"
                if provider_status == "APPROVED"
                and dataset_status == "PUBLIC_APPROVED"
                and license_status == "PUBLIC_APPROVED"
                else "denied",
            )
        )
    return AdminProviderGovernanceStatus(items=items, checked_at=checked_at)


def _quarantine(checked_at: datetime) -> AdminQuarantineStatus:
    try:
        price = _db_rows("SELECT count(*) FROM market_data_quarantine")[0][0]
    except Exception:
        price = 0
    try:
        corporate = _db_rows("SELECT count(*) FROM corporate_actions_quarantine")[0][0]
    except Exception:
        corporate = 0
    return AdminQuarantineStatus(
        price_anomalies=int(price),
        corporate_actions=int(corporate),
        checked_at=checked_at,
    )


def _locks(checked_at: datetime) -> AdminLocksStatus:
    items: list[AdminLockStatus] = []
    try:
        client = _redis_client()
        for key in client.scan_iter(match="market_data:lock:*", count=100):
            ttl = client.ttl(key)
            items.append(
                AdminLockStatus(
                    name="market_data_refresh",
                    acquired_at=checked_at,
                    ttl_seconds=ttl if ttl >= 0 else None,
                )
            )
    except Exception:
        pass
    return AdminLocksStatus(items=items, checked_at=checked_at)


def _editorial(checked_at: datetime) -> AdminEditorialConsumptionStatus:
    try:
        published = _db_rows(
            "SELECT published_at FROM editorial_posts WHERE status='PUBLISHED' "
            "ORDER BY published_at DESC LIMIT 1"
        )
        archived = _db_rows(
            "SELECT count(*) FROM editorial_post_versions WHERE status='SUPERSEDED'"
        )
        return AdminEditorialConsumptionStatus(
            last_published_at=published[0][0] if published else None,
            archived_versions=int(archived[0][0]) if archived else 0,
            checked_at=checked_at,
        )
    except Exception:
        return AdminEditorialConsumptionStatus(archived_versions=0, checked_at=checked_at)


def _volumetrics(checked_at: datetime) -> AdminVolumetricStatus:
    try:
        users = _db_rows("SELECT count(*) FROM users WHERE status='ACTIVE'")[0][0]
    except Exception:
        users = 0
    try:
        portfolios = _db_rows("SELECT count(*) FROM portfolios WHERE archived_at IS NULL")[0][0]
    except Exception:
        portfolios = 0
    return AdminVolumetricStatus(
        active_users=int(users), active_portfolios=int(portfolios), checked_at=checked_at
    )


def build_admin_system(request_id: str) -> AdminSystemResponse:
    checked_at = _now()
    return AdminSystemResponse(
        request_id=request_id,
        checked_at=checked_at,
        postgres=_postgres_status(checked_at),
        redis=_redis_status(checked_at),
        openapi=AdminContractStatus(version=get_settings().api_version, checked_at=checked_at),
        background_jobs=_background_jobs(checked_at),
        providers=_providers(checked_at),
        quarantine=_quarantine(checked_at),
        locks=_locks(checked_at),
        editorial=_editorial(checked_at),
        volumetrics=_volumetrics(checked_at),
    )
