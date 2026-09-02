"""Deterministic freshness policy for market data.

Freshness is deliberately independent from :class:`DataLevel`: a delayed or
end-of-day value can be fresh for its declared delivery mode without being
presented as real time.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.providers.models import DataLevel, Freshness


@dataclass(frozen=True)
class FreshnessResult:
    freshness: Freshness
    reason_code: str
    computed_at: datetime
    source_timestamp: datetime | None
    max_age: timedelta
    stale_after: timedelta
    timezone: ZoneInfo

    @property
    def ttl(self) -> int:
        return max(0, int(self.max_age.total_seconds()))


@dataclass(frozen=True)
class WeekdayMarketCalendar:
    timezone_name: str

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    def is_market_open(self, instant: datetime) -> bool:
        local = instant.astimezone(self.timezone)
        return local.weekday() < 5


_TTL_SECONDS: dict[DataLevel, dict[str, tuple[int, int]]] = {
    DataLevel.REAL_TIME: {
        "quote": (60, 300),
        "history": (300, 3600),
        "default": (60, 300),
    },
    DataLevel.DELAYED: {
        "quote": (900, 7200),
        "history": (1800, 86400),
        "default": (900, 7200),
    },
    DataLevel.EOD: {
        "quote": (86400, 604800),
        "history": (86400, 2592000),
        "eod": (86400, 604800),
        "default": (86400, 604800),
    },
    DataLevel.DEMO: {
        "quote": (300, 3600),
        "history": (3600, 86400),
        "default": (300, 3600),
    },
}


def ttl_for(data_level: DataLevel, data_type: str = "quote") -> int:
    """Return the fresh TTL in seconds for a declared data level."""

    policy = _TTL_SECONDS[data_level]
    return policy.get(data_type, policy["default"])[0]


def _policy(data_level: DataLevel, data_type: str) -> tuple[timedelta, timedelta]:
    fresh, stale = _TTL_SECONDS[data_level].get(data_type, _TTL_SECONDS[data_level]["default"])
    return timedelta(seconds=fresh), timedelta(seconds=stale)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def compute_freshness(
    data_level: DataLevel,
    source_timestamp: datetime | None,
    *,
    now: datetime | None = None,
    data_type: str = "quote",
    timezone_name: str = "UTC",
) -> FreshnessResult:
    """Compute freshness without consulting a provider or system clock implicitly."""

    zone = ZoneInfo(timezone_name)
    computed_at = _aware(now or datetime.now(timezone.utc))
    fresh_after, stale_after = _policy(data_level, data_type)
    source = _aware(source_timestamp) if source_timestamp is not None else None

    if source is None:
        status, reason = Freshness.UNAVAILABLE, "MISSING_SOURCE_TIMESTAMP"
    else:
        age = computed_at - source
        if age.total_seconds() < 0:
            status, reason = Freshness.UNAVAILABLE, "FUTURE_SOURCE_TIMESTAMP"
        elif age <= fresh_after:
            status, reason = Freshness.FRESH, "WITHIN_TTL"
        elif age <= stale_after:
            status, reason = Freshness.STALE, "PAST_TTL"
        else:
            status, reason = Freshness.UNAVAILABLE, "STALE_WINDOW_EXPIRED"

    return FreshnessResult(
        freshness=status,
        reason_code=reason,
        computed_at=computed_at.astimezone(zone),
        source_timestamp=source.astimezone(zone) if source else None,
        max_age=fresh_after,
        stale_after=stale_after,
        timezone=zone,
    )
