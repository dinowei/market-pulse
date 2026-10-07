"""H-19 (ADR-017): authenticated requests are limited per user, everything else per IP."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

import app.routers as routers
from app.auth.service import (
    AuthService,
    InMemoryAuthStore,
    InMemoryRateLimiter,
    InMemorySessionStore,
)
from app.contracts import AuthUserResponse
from app.main import app

ME = "/api/v1/auth/me"
LIMIT = 3


class _CountingSessions(InMemorySessionStore):
    def __init__(self) -> None:
        super().__init__()
        self.reads = 0

    def get(self, token_hash: str):
        self.reads += 1
        return super().get(token_hash)


def _setup(
    monkeypatch,
) -> tuple[TestClient, InMemoryRateLimiter, _CountingSessions, dict[str, str]]:
    sessions = _CountingSessions()
    auth = AuthService(store=InMemoryAuthStore(), sessions=sessions, limiter=InMemoryRateLimiter())
    tokens: dict[str, str] = {}
    for name in ("ana", "bia"):
        user = AuthUserResponse(id=str(uuid4()), email=f"{name}@example.invalid", status="ACTIVE")
        token = uuid4().hex
        sessions.create(auth._hash_token(token), user, datetime.now(UTC) + timedelta(hours=1), 3600)
        tokens[name] = token
    monkeypatch.setattr(routers, "get_auth_service", lambda: auth)
    limiter = InMemoryRateLimiter(max_attempts=LIMIT)
    app.state.rate_limiter = limiter
    return TestClient(app), limiter, sessions, tokens


def _get(client: TestClient, token: str | None = None) -> int:
    client.cookies.clear()
    if token:
        client.cookies.set("market_pulse_session", token)
    return client.get(ME).status_code


def test_two_users_behind_one_address_do_not_share_a_bucket(monkeypatch) -> None:
    client, limiter, _, tokens = _setup(monkeypatch)
    try:
        assert [_get(client, tokens["ana"]) for _ in range(LIMIT)] == [200] * LIMIT
        assert _get(client, tokens["ana"]) == 429, "ana's own limit still applies"
        assert [_get(client, tokens["bia"]) for _ in range(LIMIT)] == [200] * LIMIT
        assert all(key.startswith("rate_limit:standard:user:") for key in limiter.counts)
    finally:
        app.state.rate_limiter = None


def test_forged_or_unknown_cookies_fall_back_to_the_shared_ip_bucket(monkeypatch) -> None:
    client, limiter, _, _ = _setup(monkeypatch)
    try:
        statuses = [_get(client, uuid4().hex) for _ in range(LIMIT + 2)]
        assert statuses[:LIMIT] == [401] * LIMIT
        assert statuses[LIMIT:] == [429, 429], "a new fake cookie must not buy a new quota"
        assert set(limiter.counts) == {"rate_limit:standard:ip:testclient"}
    finally:
        app.state.rate_limiter = None


def test_anonymous_requests_use_the_ip_bucket(monkeypatch) -> None:
    client, limiter, _, _ = _setup(monkeypatch)
    try:
        assert [_get(client) for _ in range(LIMIT)] == [401] * LIMIT
        assert _get(client) == 429
        assert set(limiter.counts) == {"rate_limit:standard:ip:testclient"}
    finally:
        app.state.rate_limiter = None


def test_the_session_is_read_once_per_request(monkeypatch) -> None:
    client, _, sessions, tokens = _setup(monkeypatch)
    try:
        assert _get(client, tokens["ana"]) == 200
        assert sessions.reads == 1, "the route reuses the user validated by the middleware"
    finally:
        app.state.rate_limiter = None


def test_a_revoked_session_is_not_treated_as_a_user(monkeypatch) -> None:
    client, limiter, sessions, tokens = _setup(monkeypatch)
    try:
        sessions.revoke(AuthService._hash_token(tokens["ana"]))
        assert _get(client, tokens["ana"]) == 401
        assert set(limiter.counts) == {"rate_limit:standard:ip:testclient"}
    finally:
        app.state.rate_limiter = None
