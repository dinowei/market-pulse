import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.routers as routers
from app.auth.service import (
    AuthService,
    InMemoryAuthStore,
    InMemoryRateLimiter,
    InMemorySessionStore,
)
from app.core.config import (
    ProductionConfigurationError,
    Settings,
    registration_open,
    validate_production_settings,
)
from app.main import app

API_ROOT = Path(__file__).resolve().parents[1]


def _staging_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "staging",
        "database_url": "postgresql://market_pulse:"
        + secrets.token_hex(8)
        + "@staging.db:5432/market_pulse_staging",
        "redis_url": "redis://staging-kv:6379",
        "internal_refresh_secret": secrets.token_hex(16),
        "cors_origins": ["https://staging.example.test"],
        "demo_enabled": False,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.parametrize(
    ("environment", "explicit", "expected"),
    [
        ("local", None, True),
        ("test", None, True),
        ("staging", None, False),
        ("production", None, False),
        ("staging", True, True),
        ("local", False, False),
    ],
)
def test_registration_fails_closed_in_protected_environments(
    environment: str, explicit: bool | None, expected: bool
) -> None:
    settings = Settings(environment=environment, registration_enabled=explicit)
    assert registration_open(settings) is expected


def test_blank_registration_setting_falls_back_to_environment_default() -> None:
    assert Settings(environment="staging", registration_enabled="").registration_enabled is None
    assert Settings(environment="staging", registration_enabled="true").registration_enabled


def test_register_returns_404_when_registration_is_closed(monkeypatch) -> None:
    auth = AuthService(
        store=InMemoryAuthStore(), sessions=InMemorySessionStore(), limiter=InMemoryRateLimiter()
    )
    monkeypatch.setattr(routers, "get_auth_service", lambda: auth)
    monkeypatch.setattr(routers, "get_settings", lambda: Settings(registration_enabled=False))

    response = TestClient(app).post(
        "/api/v1/auth/register",
        json={"email": "closed@example.com", "password": "Strong-password-123"},
    )

    assert response.status_code == 404
    assert auth.store.find_user("closed@example.com") is None


@pytest.mark.parametrize("samesite", ["none", "None", "invalid"])
def test_protected_environments_reject_cross_site_session_cookie(samesite: str) -> None:
    with pytest.raises(ProductionConfigurationError, match="AUTH_COOKIE_SAMESITE"):
        validate_production_settings(_staging_settings(auth_cookie_samesite=samesite))


@pytest.mark.parametrize("samesite", ["lax", "strict"])
def test_protected_environments_accept_first_party_session_cookie(samesite: str) -> None:
    validate_production_settings(_staging_settings(auth_cookie_samesite=samesite))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('["https://web.example.test"]', ["https://web.example.test"]),
        ("https://web.example.test", ["https://web.example.test"]),
        ("https://web.example.test/", ["https://web.example.test"]),
        (
            " https://a.example.test , https://b.example.test/ ",
            ["https://a.example.test", "https://b.example.test"],
        ),
        ('["https://a.example.test/", " "]', ["https://a.example.test"]),
    ],
)
def test_cors_origins_accept_json_or_comma_separated_env(monkeypatch, raw, expected) -> None:
    monkeypatch.setenv("MARKET_PULSE_CORS_ORIGINS", raw)
    assert Settings().cors_origins == expected


def test_blank_cors_origins_fail_with_a_clear_production_error(monkeypatch) -> None:
    monkeypatch.setenv("MARKET_PULSE_CORS_ORIGINS", "")
    settings = Settings()
    assert settings.cors_origins == []
    with pytest.raises(ProductionConfigurationError, match="CORS_ORIGINS"):
        validate_production_settings(_staging_settings(cors_origins=settings.cors_origins))


def test_local_environment_keeps_interactive_docs() -> None:
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert {"/docs", "/redoc", "/openapi.json"} <= paths


def test_staging_hides_interactive_docs_but_keeps_schema_generation() -> None:
    probe = (
        "import json\n"
        "from app.main import app\n"
        "paths = sorted(r.path for r in app.routes if hasattr(r, 'path'))\n"
        "print(json.dumps({'paths': paths, 'schema': bool(app.openapi()['paths'])}))\n"
    )
    env = {
        **os.environ,
        "MARKET_PULSE_ENVIRONMENT": "staging",
        "MARKET_PULSE_DATABASE_URL": str(_staging_settings().database_url),
        "MARKET_PULSE_REDIS_URL": "redis://staging-kv:6379",
        "MARKET_PULSE_INTERNAL_REFRESH_SECRET": secrets.token_hex(16),
        "MARKET_PULSE_CORS_ORIGINS": '["https://staging.example.test"]',
        "MARKET_PULSE_DEMO_ENABLED": "false",
    }
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=API_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stderr[-2000:]
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert not {"/docs", "/redoc", "/openapi.json"} & set(report["paths"])
    assert "/health/live" in report["paths"]
    assert report["schema"] is True
