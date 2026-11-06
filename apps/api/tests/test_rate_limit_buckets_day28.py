"""Telemetry has its own rate-limit bucket and cannot drain the standard one.

Found by the E2E on 2026-10-01: anonymous Web Vitals beacons shared the 30/60 s "standard"
bucket with the authenticated routes, so GET /portfolios and /watchlists answered 429.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.middleware import TELEMETRY_RATE_LIMIT_MAX

TELEMETRY = "/api/v1/telemetry/web-vitals"
STANDARD_LIMIT = 30


class _CountingLimiter:
    """Has no max_attempts attribute, so the middleware applies each bucket's own limit."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def allow(
        self, key: str, window_seconds: int | None = None, max_attempts: int | None = None
    ) -> bool:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key] <= (max_attempts or 0)


def _client(limiter: _CountingLimiter) -> TestClient:
    app.state.rate_limiter = limiter
    return TestClient(app)


def test_telemetry_limit_is_30_per_60_seconds() -> None:
    assert TELEMETRY_RATE_LIMIT_MAX == 30


def test_telemetry_exhausting_its_bucket_does_not_touch_the_standard_bucket() -> None:
    limiter = _CountingLimiter()
    client = _client(limiter)
    try:
        for _ in range(TELEMETRY_RATE_LIMIT_MAX):
            assert client.post(TELEMETRY, json={}).status_code == 422
        blocked = client.post(TELEMETRY, json={})
        assert blocked.status_code == 429 and blocked.headers["Retry-After"] == "60"
        # The whole standard bucket is still available (401: unauthenticated, not 429).
        for _ in range(STANDARD_LIMIT):
            assert client.get("/api/v1/portfolios").status_code == 401
        # The standard bucket is keyed by subject since H-19 (ADR-017): ip:<addr> or user:<id>.
        assert set(limiter.counts) == {
            "rate_limit:telemetry:ip:testclient",
            "rate_limit:standard:ip:testclient",
        }
    finally:
        app.state.rate_limiter = None


def test_standard_bucket_still_blocks_the_31st_request() -> None:
    client = _client(_CountingLimiter())
    try:
        for _ in range(STANDARD_LIMIT):
            assert client.get("/api/v1/portfolios").status_code == 401
        assert client.get("/api/v1/portfolios").status_code == 429
        assert client.get("/api/v1/watchlists").status_code == 429, "same standard bucket"
        # The telemetry bucket is untouched by it.
        assert client.post(TELEMETRY, json={}).status_code == 422
    finally:
        app.state.rate_limiter = None
