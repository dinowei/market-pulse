"""H-24: auth stores share one Redis client per process and configuration."""

from app.auth.service import AuthService, InMemoryAuthStore, RedisRateLimiter, RedisSessionStore
from app.core.config import Settings
from app.core.redis_client import shared_redis

URL = "redis://127.0.0.1:6399/15"


def test_sessions_and_limiter_reuse_one_client_across_services() -> None:
    settings = Settings(redis_url=URL, cache_timeout_seconds=0.2)
    first = AuthService(store=InMemoryAuthStore(), settings=settings)
    second = AuthService(store=InMemoryAuthStore(), settings=settings)
    assert isinstance(first.sessions, RedisSessionStore)
    assert isinstance(first.limiter, RedisRateLimiter)
    assert first.sessions.client is second.sessions.client is first.limiter.client
    assert first.sessions.client is shared_redis(URL, 0.2)


def test_a_different_configuration_gets_its_own_client() -> None:
    assert shared_redis(URL, 0.2) is not shared_redis(URL, 0.5)
    assert shared_redis(URL, 0.2) is not shared_redis("redis://127.0.0.1:6399/14", 0.2)
