from __future__ import annotations

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


def service() -> AuthService:
    return AuthService(
        store=InMemoryAuthStore(), sessions=InMemorySessionStore(), limiter=InMemoryRateLimiter()
    )


def test_register_normalizes_email_and_never_returns_hash(monkeypatch) -> None:
    auth = service()
    monkeypatch.setattr(routers, "get_auth_service", lambda: auth)

    response = TestClient(app).post(
        "/api/v1/auth/register",
        json={"email": "  USER@Example.COM ", "password": "Strong-password-123"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],
        "email": "user@example.com",
        "status": "ACTIVE",
    }
    assert "password" not in response.text and "hash" not in response.text


def test_password_policy_and_invalid_email_are_rejected(monkeypatch) -> None:
    auth = service()
    monkeypatch.setattr(routers, "get_auth_service", lambda: auth)
    client = TestClient(app)

    assert (
        client.post("/api/v1/auth/register", json={"email": "bad", "password": "weak"}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/auth/register", json={"email": "a@example.com", "password": "short"}
        ).status_code
        == 422
    )


def test_login_sets_httponly_cookie_without_returning_token(monkeypatch) -> None:
    auth = service()
    monkeypatch.setattr(routers, "get_auth_service", lambda: auth)
    client = TestClient(app)
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "Strong-password-123"},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "Strong-password-123"},
    )

    assert response.status_code == 200
    assert "session" not in response.text.lower()
    cookie = response.cookies.get("market_pulse_session")
    assert cookie and len(cookie) >= 32
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]


def test_invalid_login_is_generic_and_me_requires_session(monkeypatch) -> None:
    auth = service()
    monkeypatch.setattr(routers, "get_auth_service", lambda: auth)
    client = TestClient(app)
    invalid = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "Wrong-password-123"},
    )
    assert invalid.status_code == 401
    assert "missing@example.com" not in invalid.text
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_and_logout_revoke_opaque_session(monkeypatch) -> None:
    auth = service()
    monkeypatch.setattr(routers, "get_auth_service", lambda: auth)
    client = TestClient(app)
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "Strong-password-123"},
    )
    client.post(
        "/api/v1/auth/login", json={"email": "user@example.com", "password": "Strong-password-123"}
    )

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"
    assert "token" not in me.text.lower()

    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_public_market_data_remains_public(monkeypatch) -> None:
    auth = service()
    monkeypatch.setattr(routers, "get_auth_service", lambda: auth)
    client = TestClient(app)
    assert client.get("/api/v1/market-data/quotes/equity.br.b3.petr4").status_code == 200
    assert client.get("/api/v1/market-data/history/equity.br.b3.petr4?period=1D").status_code == 200


def test_owner_dependency_shape_is_minimal() -> None:
    assert AuthUserResponse.model_fields.keys() >= {"id", "email", "status"}
