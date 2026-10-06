"""ADR-009: CSRF runs before the rate limit and security headers wrap every response."""

from fastapi.testclient import TestClient

from app.auth.service import InMemoryRateLimiter
from app.main import app

FORGED = {"Origin": "https://untrusted.invalid"}
ALLOWED = {"Origin": "http://localhost:3000"}
CREDENTIALS = {"email": "person@example.invalid", "password": "Str0ng-password-123"}
SECURITY_HEADERS = (
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
)


class _UnavailableLimiter:
    def allow(self, key: str, window_seconds=None, max_attempts=None) -> bool:
        raise ConnectionError("redis down")


def _with_limiter(limiter) -> TestClient:
    app.state.rate_limiter = limiter
    return TestClient(app)


def test_forged_request_is_refused_by_csrf_even_when_rate_limiter_is_down() -> None:
    try:
        client = _with_limiter(_UnavailableLimiter())
        response = client.post("/api/v1/auth/login", json=CREDENTIALS, headers=FORGED)
        assert response.status_code == 403
        assert "CSRF" in response.json()["detail"]

        # Same path with an allowed origin still fails closed on the auth bucket.
        assert (
            client.post("/api/v1/auth/login", json=CREDENTIALS, headers=ALLOWED).status_code
            == 503
        )
    finally:
        app.state.rate_limiter = None


def test_forged_requests_do_not_consume_the_victims_quota() -> None:
    limiter = InMemoryRateLimiter(max_attempts=2)
    try:
        client = _with_limiter(limiter)
        for _ in range(5):
            assert (
                client.post("/api/v1/auth/login", json=CREDENTIALS, headers=FORGED).status_code
                == 403
            )
        assert limiter.counts == {}

        for _ in range(2):
            assert (
                client.post("/api/v1/auth/login", json=CREDENTIALS, headers=ALLOWED).status_code
                != 429
            )
        third = client.post("/api/v1/auth/login", json=CREDENTIALS, headers=ALLOWED)
        assert third.status_code == 429
    finally:
        app.state.rate_limiter = None


def test_rate_limit_still_counts_headerless_non_browser_clients() -> None:
    limiter = InMemoryRateLimiter(max_attempts=1)
    try:
        client = _with_limiter(limiter)
        assert client.post("/api/v1/auth/login", json=CREDENTIALS).status_code != 429
        assert client.post("/api/v1/auth/login", json=CREDENTIALS).status_code == 429
    finally:
        app.state.rate_limiter = None


def test_security_headers_are_present_on_middleware_errors() -> None:
    limiter = InMemoryRateLimiter(max_attempts=0)
    try:
        client = _with_limiter(limiter)
        forged = client.post("/api/v1/auth/login", json=CREDENTIALS, headers=FORGED)
        limited = client.post("/api/v1/auth/login", json=CREDENTIALS, headers=ALLOWED)
    finally:
        app.state.rate_limiter = None

    assert forged.status_code == 403
    assert limited.status_code == 429
    for response in (forged, limited):
        for header in SECURITY_HEADERS:
            assert response.headers.get(header), (response.status_code, header)
        assert response.headers.get("X-Request-ID")
