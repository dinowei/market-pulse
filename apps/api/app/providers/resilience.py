import random
import time
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Callable, TypeVar


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.1
    max_delay_seconds: float = 2.0

    def __post_init__(self) -> None:
        if not 1 <= self.max_attempts <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if self.base_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("retry delays cannot be negative")


T = TypeVar("T")


def retry_call(operation: Callable[[], T], policy: RetryPolicy) -> T:
    for attempt in range(policy.max_attempts):
        try:
            return operation()
        except (TimeoutError, ConnectionError):
            if attempt == policy.max_attempts - 1:
                raise
            delay = min(policy.max_delay_seconds, policy.base_delay_seconds * (2**attempt))
            if delay:
                time.sleep(random.uniform(0, delay))
    raise RuntimeError("unreachable")


# --- 429 / Retry-After and circuit breaker (ADR-025) ---------------------------------------

MAX_RETRY_AFTER_SECONDS = 3600.0


def parse_retry_after(value: str | None, now: datetime) -> float | None:
    """Seconds to wait from a Retry-After header (delta-seconds or HTTP-date), bounded."""

    if value is None or not value.strip():
        return None
    text = value.strip()
    if text.isdigit():
        return min(float(text), MAX_RETRY_AFTER_SECONDS)
    try:
        moment = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        return None
    return min(max(0.0, (moment - now).total_seconds()), MAX_RETRY_AFTER_SECONDS)


def backoff_delay(attempt: int, policy: RetryPolicy, retry_after: float | None = None) -> float:
    """The provider's Retry-After wins over our own exponential backoff with jitter."""

    if retry_after is not None:
        return retry_after
    ceiling = min(policy.max_delay_seconds, policy.base_delay_seconds * (2**attempt))
    return random.uniform(0, ceiling) if ceiling else 0.0


class CircuitBreaker:
    """Closed -> open after N consecutive failures -> half-open after a cooldown.

    In-process state: the staging API runs one instance (render.yaml). A Redis-backed
    breaker is needed only with more than one instance.
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        failure_threshold: int,
        cooldown_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1 or cooldown_seconds <= 0:
            raise ValueError("threshold must be >= 1 and cooldown > 0")
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return self.CLOSED
        if self._clock() - self._opened_at >= self.cooldown_seconds:
            return self.HALF_OPEN
        return self.OPEN

    def allow_request(self) -> bool:
        return self.state != self.OPEN

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        if self.state == self.HALF_OPEN:
            self._opened_at = self._clock()
            return
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = self._clock()
