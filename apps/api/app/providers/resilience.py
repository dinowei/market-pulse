import random
import time
from dataclasses import dataclass
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
