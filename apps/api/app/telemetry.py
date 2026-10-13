"""Anonymous Core Web Vitals aggregation with a strict no-PII boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg

from app.core.config import Settings, get_settings


class TelemetryPIIError(ValueError):
    """Raised when a telemetry payload contains an identifiable field."""


PII_FIELD_FRAGMENTS = frozenset(
    {
        "address",
        "cookie",
        "email",
        "ip",
        "name",
        "password",
        "phone",
        "session",
        "token",
        "user",
    }
)
ALLOWED_METRICS = frozenset({"LCP", "INP", "CLS"})


@dataclass(frozen=True)
class WebVitalsAggregate:
    metric: str
    value: Decimal
    route: str
    sample_count: int
    observed_at: datetime


def _contains_pii_key(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).casefold()
            if any(fragment in normalized for fragment in PII_FIELD_FRAGMENTS):
                return str(key)
            found = _contains_pii_key(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _contains_pii_key(child)
            if found:
                return found
    return None


def validate_web_vitals_payload(payload: dict[str, Any]) -> WebVitalsAggregate:
    pii_key = _contains_pii_key(payload)
    if pii_key:
        raise TelemetryPIIError(f"telemetry field is not allowed: {pii_key}")
    metric = payload.get("metric")
    if metric not in ALLOWED_METRICS:
        raise ValueError("metric must be one of LCP, INP or CLS")
    try:
        value = Decimal(str(payload.get("value")))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("value must be a finite Decimal") from exc
    if not value.is_finite() or value < 0:
        raise ValueError("value must be a finite Decimal")
    route = payload.get("route")
    if not isinstance(route, str) or not route.startswith("/") or len(route) > 160:
        raise ValueError("route must be a relative path")
    sample_count = payload.get("sample_count", 1)
    if (
        not isinstance(sample_count, int)
        or isinstance(sample_count, bool)
        or not 1 <= sample_count <= 100000
    ):
        raise ValueError("sample_count must be between 1 and 100000")
    observed_at = payload.get("observed_at")
    if observed_at is None:
        timestamp = datetime.now(timezone.utc)
    else:
        try:
            timestamp = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("observed_at must be ISO-8601") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        timestamp = timestamp.astimezone(timezone.utc)
    return WebVitalsAggregate(metric, value, route, sample_count, timestamp)


class PostgresWebVitalsService:
    """Persist only daily route/metric aggregates; raw payloads are discarded."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _connection(self):
        return psycopg.connect(self.settings.database_url)

    def record(self, aggregate: WebVitalsAggregate) -> None:
        bucket = aggregate.observed_at.date()
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO web_vital_metrics "
                "(route,metric,bucket_start,value_sum,sample_count,updated_at) "
                "VALUES (%s,%s,%s,%s,%s,now()) "
                "ON CONFLICT (route,metric,bucket_start) DO UPDATE SET "
                "value_sum=web_vital_metrics.value_sum + EXCLUDED.value_sum, "
                "sample_count=web_vital_metrics.sample_count + EXCLUDED.sample_count, "
                "updated_at=now()",
                (
                    aggregate.route,
                    aggregate.metric,
                    bucket,
                    aggregate.value * aggregate.sample_count,
                    aggregate.sample_count,
                ),
            )
            connection.commit()
