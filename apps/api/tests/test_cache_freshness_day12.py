from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.market_data.cache import (
    LICENSE_BLOCKED,
    NOT_FOUND,
    CacheAsideService,
    CacheEnvelope,
    CacheKey,
    DistributedLock,
    MemoryCacheBackend,
    NegativeCache,
)
from app.market_data.freshness import compute_freshness, ttl_for
from app.providers.models import DataLevel, Freshness

UTC = timezone.utc


def envelope(
    *,
    value: object = Decimal("123.45"),
    level: DataLevel = DataLevel.DELAYED,
    freshness: Freshness = Freshness.FRESH,
    source_timestamp: datetime | None = None,
    cached_at: datetime | None = None,
) -> CacheEnvelope:
    now = cached_at or datetime(2026, 9, 1, 14, 0, tzinfo=UTC)
    source_timestamp = source_timestamp or now
    return CacheEnvelope(
        value=value,
        source="demo-provider",
        dataset="quotes",
        data_level=level,
        freshness=freshness,
        source_timestamp=source_timestamp,
        collected_at=now,
        cached_at=now,
        fresh_until=now + timedelta(minutes=5),
        stale_until=now + timedelta(hours=1),
        currency="BRL",
    )


def test_key_is_granular_and_has_no_secret_material():
    key = CacheKey.quote(dataset="quotes", canonical_id="equity.br.b3.petr4")
    assert key == "market_data:quote:quotes:equity.br.b3.petr4"
    assert "secret" not in key.lower()
    assert CacheKey.history("quotes", "equity.br.b3.petr4", "1d", "raw") != key


def test_cache_miss_loads_and_stores_value():
    backend = MemoryCacheBackend()
    service = CacheAsideService(backend, now=lambda: datetime(2026, 9, 1, 14, 0, tzinfo=UTC))
    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return envelope()

    result = service.get_or_load(CacheKey.quote("quotes", "equity.br.b3.petr4"), loader)
    assert result.value == Decimal("123.45")
    assert calls == 1
    assert service.get_or_load(
        CacheKey.quote("quotes", "equity.br.b3.petr4"), loader
    ).value == Decimal("123.45")
    assert calls == 1


def test_cache_hit_preserves_provenance_and_data_level():
    backend = MemoryCacheBackend()
    source = envelope(level=DataLevel.EOD, freshness=Freshness.FRESH)
    backend.set("k", source, ttl=3600)
    result = CacheAsideService(
        backend, now=lambda: datetime(2026, 9, 1, 14, 0, tzinfo=UTC)
    ).get_or_load("k", lambda: pytest.fail("must not load"))
    assert result.source == "demo-provider"
    assert result.data_level is DataLevel.EOD
    assert result.freshness is Freshness.FRESH


def test_eod_is_never_promoted_to_realtime_and_demo_remains_demo():
    eod = envelope(level=DataLevel.EOD)
    demo = envelope(level=DataLevel.DEMO)
    assert eod.data_level is DataLevel.EOD
    assert demo.data_level is DataLevel.DEMO
    assert compute_freshness(DataLevel.DEMO, demo.source_timestamp).freshness is Freshness.STALE
    assert ttl_for(DataLevel.EOD, "quote") > 0


def test_freshness_uses_explicit_ttl_and_marks_stale_then_unavailable():
    captured = datetime(2026, 9, 1, 14, 0, tzinfo=UTC)
    fresh = compute_freshness(
        DataLevel.DELAYED, captured, now=captured + timedelta(minutes=1), data_type="quote"
    )
    stale = compute_freshness(
        DataLevel.DELAYED, captured, now=captured + timedelta(minutes=20), data_type="quote"
    )
    unavailable = compute_freshness(
        DataLevel.DELAYED, captured, now=captured + timedelta(hours=3), data_type="quote"
    )
    assert fresh.freshness is Freshness.FRESH
    assert stale.freshness is Freshness.STALE
    assert unavailable.freshness is Freshness.UNAVAILABLE


def test_missing_or_future_source_timestamp_is_unavailable():
    now = datetime(2026, 9, 1, 14, 0, tzinfo=UTC)
    assert compute_freshness(DataLevel.REAL_TIME, None, now=now).freshness is Freshness.UNAVAILABLE
    assert (
        compute_freshness(DataLevel.REAL_TIME, now + timedelta(minutes=1), now=now).freshness
        is Freshness.UNAVAILABLE
    )


def test_eod_can_be_fresh_after_market_close_with_explicit_timezone():
    now = datetime(2026, 9, 1, 22, 0, tzinfo=UTC)  # 19:00 in Sao Paulo
    result = compute_freshness(
        DataLevel.EOD,
        datetime(2026, 9, 1, 20, 0, tzinfo=UTC),
        now=now,
        data_type="eod",
        timezone_name="America/Sao_Paulo",
    )
    assert result.freshness is Freshness.FRESH


def test_timezone_and_dst_are_deterministic():
    now = datetime(2026, 3, 8, 15, 0, tzinfo=UTC)
    source = datetime(2026, 3, 8, 14, 59, tzinfo=UTC)
    result = compute_freshness(
        DataLevel.REAL_TIME, source, now=now, timezone_name="America/New_York"
    )
    assert result.freshness is Freshness.FRESH
    assert result.timezone == ZoneInfo("America/New_York")


def test_negative_cache_has_short_ttl_and_distinguishes_license_block():
    negative = NegativeCache(MemoryCacheBackend())
    negative.put("query:petr4", NOT_FOUND)
    negative.put("query:blocked", LICENSE_BLOCKED)
    assert negative.get("query:petr4") == NOT_FOUND
    assert negative.get("query:blocked") == LICENSE_BLOCKED
    assert negative.ttl_seconds <= 120


def test_redis_failure_falls_back_to_source_and_source_failure_uses_stale():
    class BrokenBackend(MemoryCacheBackend):
        def get(self, key):
            raise ConnectionError("redis unavailable")

        def set(self, key, value, ttl):
            raise ConnectionError("redis unavailable")

    service = CacheAsideService(BrokenBackend())
    assert service.get_or_load("k", lambda: envelope()).value == Decimal("123.45")
    stale = envelope(freshness=Freshness.STALE)
    service = CacheAsideService(BrokenBackend())
    assert (
        service.get_or_load(
            "k", lambda: (_ for _ in ()).throw(RuntimeError("provider down")), stale=stale
        ).freshness
        is Freshness.STALE
    )
    assert service.last_error_code == "SOURCE_UNAVAILABLE"


def test_no_stale_candidate_returns_unavailable_without_secret():
    service = CacheAsideService(MemoryCacheBackend())
    result = service.get_or_load("k", lambda: (_ for _ in ()).throw(RuntimeError("provider down")))
    assert result.freshness is Freshness.UNAVAILABLE
    assert "provider down" not in service.last_error_message


def test_granular_invalidation_does_not_flush_unrelated_keys():
    backend = MemoryCacheBackend()
    backend.set("market_data:quote:quotes:a", envelope(), ttl=100)
    backend.set("market_data:quote:quotes:b", envelope(), ttl=100)
    backend.invalidate(CacheKey.quote("quotes", "a"))
    assert backend.get("market_data:quote:quotes:a") is None
    assert backend.get("market_data:quote:quotes:b") is not None


def test_distributed_lock_is_owner_only_and_expires():
    backend = MemoryCacheBackend()
    lock1 = DistributedLock(backend, "market_data:lock:quotes:a", ttl=2, owner="owner-1")
    lock2 = DistributedLock(backend, "market_data:lock:quotes:a", ttl=2, owner="owner-2")
    assert lock1.acquire()
    assert not lock2.acquire()
    assert not lock2.release()
    assert lock1.release()
    assert lock2.acquire()


def test_decimal_payload_round_trips_without_float_conversion():
    backend = MemoryCacheBackend()
    service = CacheAsideService(backend)
    result = service.get_or_load("decimal", lambda: envelope(value={"price": Decimal("1.10")}))
    assert result.value["price"] == Decimal("1.10")
    assert not isinstance(result.value["price"], float)
