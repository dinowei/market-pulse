"""Provider-agnostic cache-aside primitives for market data."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Protocol

from app.providers.models import DataLevel, Freshness

NOT_FOUND = "NOT_FOUND"
OUT_OF_SCOPE = "OUT_OF_SCOPE"
DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
LICENSE_BLOCKED = "LICENSE_BLOCKED"


class CacheBackend(Protocol):
    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, value: Any, ttl: int) -> None: ...

    def delete(self, key: str) -> None: ...


class CacheKey:
    """Stable, granular keys. Values are metadata identifiers, never secrets."""

    @staticmethod
    def quote(dataset: str, canonical_id: str) -> str:
        return f"market_data:quote:{dataset}:{canonical_id}"

    @staticmethod
    def history(dataset: str, canonical_id: str, timeframe: str, adjustment: str) -> str:
        return f"market_data:history:{dataset}:{canonical_id}:{timeframe}:{adjustment}"

    @staticmethod
    def fx(dataset: str, base: str, quote: str) -> str:
        return f"market_data:fx:{dataset}:{base.upper()}-{quote.upper()}"

    @staticmethod
    def negative(query: str, namespace: str = "instrument_search") -> str:
        digest = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:24]
        return f"market_data:negative:{namespace}:{digest}"

    @staticmethod
    def lock(dataset: str, identity: str) -> str:
        return f"market_data:lock:{dataset}:{identity}"


def _encode(value: Any) -> Any:
    if isinstance(value, Decimal):
        return {"__decimal__": str(value)}
    if isinstance(value, datetime):
        return {"__datetime__": value.isoformat()}
    if isinstance(value, (DataLevel, Freshness)):
        return value.value
    if isinstance(value, dict):
        return {str(k): _encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode(v) for v in value]
    return value


def _decode(value: Any) -> Any:
    if isinstance(value, dict):
        if "__decimal__" in value:
            return Decimal(value["__decimal__"])
        if "__datetime__" in value:
            return datetime.fromisoformat(value["__datetime__"])
        return {k: _decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode(v) for v in value]
    return value


@dataclass(frozen=True)
class CacheEnvelope:
    value: Any
    source: str
    dataset: str
    data_level: DataLevel
    freshness: Freshness
    source_timestamp: datetime | None
    collected_at: datetime
    cached_at: datetime
    fresh_until: datetime
    stale_until: datetime
    currency: str
    limitations: tuple[str, ...] = ()

    def to_json(self) -> str:
        payload = _encode(
            {
                "value": self.value,
                "source": self.source,
                "dataset": self.dataset,
                "data_level": self.data_level.value,
                "freshness": self.freshness.value,
                "source_timestamp": self.source_timestamp,
                "collected_at": self.collected_at,
                "cached_at": self.cached_at,
                "fresh_until": self.fresh_until,
                "stale_until": self.stale_until,
                "currency": self.currency,
                "limitations": self.limitations,
            }
        )
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def from_json(cls, raw: str | bytes) -> "CacheEnvelope":
        payload = _decode(json.loads(raw))
        return cls(
            value=payload["value"],
            source=payload["source"],
            dataset=payload["dataset"],
            data_level=DataLevel(payload["data_level"]),
            freshness=Freshness(payload["freshness"]),
            source_timestamp=payload["source_timestamp"],
            collected_at=payload["collected_at"],
            cached_at=payload["cached_at"],
            fresh_until=payload["fresh_until"],
            stale_until=payload["stale_until"],
            currency=payload["currency"],
            limitations=tuple(payload.get("limitations", ())),
        )


class MemoryCacheBackend:
    """Deterministic backend for tests and local fallback behavior."""

    def __init__(self) -> None:
        self._values: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        item = self._values.get(key)
        if item is None:
            return None
        value, expires = item
        if expires <= time.monotonic():
            self._values.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._values[key] = (value, time.monotonic() + max(1, ttl))

    def set_if_absent(self, key: str, value: Any, ttl: int) -> bool:
        if self.get(key) is not None:
            return False
        self.set(key, value, ttl)
        return True

    def compare_delete(self, key: str, owner: Any) -> bool:
        if self.get(key) != owner:
            return False
        self.delete(key)
        return True

    def delete(self, key: str) -> None:
        self._values.pop(key, None)

    def invalidate(self, key: str) -> None:
        self.delete(key)


class RedisCacheBackend:
    def __init__(self, client: Any) -> None:
        self.client = client

    def get(self, key: str) -> CacheEnvelope | None:
        raw = self.client.get(key)
        return CacheEnvelope.from_json(raw) if raw is not None else None

    def set(self, key: str, value: CacheEnvelope, ttl: int) -> None:
        self.client.set(key, value.to_json(), ex=max(1, ttl))

    def delete(self, key: str) -> None:
        self.client.delete(key)

    def invalidate(self, key: str) -> None:
        self.delete(key)

    def set_if_absent(self, key: str, value: Any, ttl: int) -> bool:
        return bool(self.client.set(key, value, ex=max(1, ttl), nx=True))

    def compare_delete(self, key: str, owner: Any) -> bool:
        script = (
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end"
        )
        return bool(self.client.eval(script, 1, key, owner))


@dataclass
class CacheAsideService:
    backend: CacheBackend
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    stale_window_seconds: int = 3600
    last_error_code: str | None = field(default=None, init=False)
    last_error_message: str | None = field(default=None, init=False)

    def _now(self) -> datetime:
        value = self.now()
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    def get_or_load(
        self,
        key: str,
        loader: Callable[[], CacheEnvelope],
        *,
        stale: CacheEnvelope | None = None,
    ) -> CacheEnvelope:
        self.last_error_code = None
        self.last_error_message = None
        cached: CacheEnvelope | None = None
        try:
            cached = self.backend.get(key)
        except Exception:
            cached = None
        if cached is not None:
            now = self._now()
            if now <= cached.fresh_until:
                return cached
            if now <= cached.stale_until:
                # Keep the stale candidate while attempting a refresh.  It is
                # served only when the source fails, with an explicit STALE
                # marker.
                stale = _with_freshness(cached, Freshness.STALE)
        try:
            loaded = loader()
            if not isinstance(loaded, CacheEnvelope):
                raise TypeError("loader must return CacheEnvelope")
            try:
                ttl = max(1, int((loaded.stale_until - self._now()).total_seconds()))
                self.backend.set(key, loaded, ttl)
            except Exception:
                pass
            return loaded
        except Exception:
            candidate = stale or cached
            if candidate is not None:
                self.last_error_code = "SOURCE_UNAVAILABLE"
                self.last_error_message = "source unavailable; stale data served"
                return _with_freshness(candidate, Freshness.STALE)
            self.last_error_code = "SOURCE_UNAVAILABLE"
            self.last_error_message = "data unavailable"
            now = self._now()
            return CacheEnvelope(
                value=None,
                source="unknown",
                dataset="unknown",
                data_level=DataLevel.DEMO,
                freshness=Freshness.UNAVAILABLE,
                source_timestamp=None,
                collected_at=now,
                cached_at=now,
                fresh_until=now,
                stale_until=now,
                currency="XXX",
            )


def _with_freshness(envelope: CacheEnvelope, freshness: Freshness) -> CacheEnvelope:
    return CacheEnvelope(**{**envelope.__dict__, "freshness": freshness})


class NegativeCache:
    ttl_seconds = 90

    def __init__(self, backend: CacheBackend) -> None:
        self.backend = backend

    def put(self, query: str, status: str) -> None:
        self.backend.set(CacheKey.negative(query), status, self.ttl_seconds)

    def get(self, query: str) -> str | None:
        return self.backend.get(CacheKey.negative(query))


class DistributedLock:
    def __init__(
        self,
        backend: MemoryCacheBackend | CacheBackend,
        key: str,
        *,
        ttl: int = 30,
        owner: str | None = None,
    ) -> None:
        self.backend = backend
        self.key = key
        self.ttl = ttl
        self.owner = owner or secrets.token_urlsafe(16)

    def acquire(self) -> bool:
        setter = getattr(self.backend, "set_if_absent", None)
        if setter is not None:
            return bool(setter(self.key, self.owner, self.ttl))
        if self.backend.get(self.key) is not None:
            return False
        self.backend.set(self.key, self.owner, self.ttl)
        return self.backend.get(self.key) == self.owner

    def release(self) -> bool:
        deleter = getattr(self.backend, "compare_delete", None)
        if deleter is not None:
            return bool(deleter(self.key, self.owner))
        if self.backend.get(self.key) != self.owner:
            return False
        self.backend.delete(self.key)
        return True
