import contextlib
import os

import pytest
import redis

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("MARKET_PULSE_ENVIRONMENT", "local")
os.environ.setdefault("MARKET_PULSE_DEMO_ALLOW_RECREATE", "true")

# get_catalog() switches to the seeded demo.* read model when demo_enabled is true,
# which hides the MASTER_CATALOG identities most tests assert against. A developer's
# local apps/api/.env may enable DEMO mode, so pin it off here (os.environ outranks
# the dotenv file) to keep runs deterministic and identical to CI. Assigned, not
# setdefault, precisely to neutralize that .env. The DEMO integration gate opts back
# in via MARKET_PULSE_DEMO_INTEGRATION=true; those tests also set what they need
# through monkeypatch.
if os.environ.get("MARKET_PULSE_DEMO_INTEGRATION") != "true":
    os.environ["MARKET_PULSE_DEMO_ENABLED"] = "false"
os.environ.setdefault(
    "MARKET_PULSE_DATABASE_URL",
    "postgresql://market_pulse:market_pulse_local_only@127.0.0.1:5432/market_pulse_demo",
)
os.environ.setdefault(
    "MARKET_PULSE_DEMO_DATABASE_URL",
    "postgresql://market_pulse:market_pulse_local_only@127.0.0.1:5432/market_pulse_demo",
)
os.environ.setdefault("MARKET_PULSE_REDIS_URL", "redis://127.0.0.1:6379/15")


def _open_rate_limit_redis():
    return redis.Redis.from_url(
        os.environ["MARKET_PULSE_REDIS_URL"],
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


@pytest.fixture(scope="session")
def _rate_limit_redis_available() -> bool:
    # RateLimitMiddleware falls back to a fresh, request-scoped InMemoryRateLimiter
    # whenever Redis is unreachable, so the cleanup below is unnecessary in that case
    # (and CI jobs that run a subset of tests have no Redis service at all).
    try:
        client = _open_rate_limit_redis()
        try:
            client.ping()
        finally:
            client.close()
    except Exception:
        return False
    return True


@pytest.fixture(autouse=True)
def _reset_rate_limit_state(_rate_limit_redis_available):
    # When Redis IS reachable its rate_limit:* keys outlive individual tests, so a
    # test that exhausts a per-IP bucket would make every later test 429. A connection
    # per test keeps this immune to the idle/stale sockets a long session produces;
    # failures are raised rather than suppressed so silent non-cleanup cannot come
    # back as confusing 429s somewhere else.
    if _rate_limit_redis_available:
        client = _open_rate_limit_redis()
        try:
            keys = list(client.scan_iter("rate_limit:*"))
            if keys:
                client.delete(*keys)
        finally:
            with contextlib.suppress(Exception):
                client.close()
    yield
