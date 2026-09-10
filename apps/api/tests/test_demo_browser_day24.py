"""Local browser integration must allow only the explicit DEMO frontend origin."""

import importlib

from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_local_demo_preflight_is_explicit_and_external_origins_are_denied(monkeypatch):
    import app.main as main

    with monkeypatch.context() as env:
        for key, value in {
            "APP_ENV": "development",
            "MARKET_PULSE_ENVIRONMENT": "local",
            "MARKET_PULSE_DEMO_ENABLED": "true",
            "MARKET_PULSE_DEMO_DATABASE_URL": "postgresql://demo:local_only@localhost/market_pulse_demo",
            "MARKET_PULSE_DATABASE_URL": "postgresql://demo:local_only@localhost/market_pulse_demo",
            "MARKET_PULSE_REDIS_URL": "redis://localhost:6379/15",
        }.items():
            env.setenv(key, value)
        get_settings.cache_clear()
        try:
            client = TestClient(importlib.reload(main).app)
            headers = {
                "origin": "http://localhost:3000",
                "access-control-request-method": "POST",
                "access-control-request-headers": "content-type",
            }
            response = client.options("/api/v1/auth/login", headers=headers)
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
            assert response.headers["access-control-allow-credentials"] == "true"
            response = client.options(
                "/api/v1/auth/login", headers={**headers, "origin": "https://untrusted.invalid"}
            )
            assert response.status_code == 400
            assert "access-control-allow-origin" not in response.headers
            response = client.post(
                "/api/v1/auth/login", headers={"origin": "https://untrusted.invalid"}, json={}
            )
            assert response.status_code == 403
            assert response.headers["content-type"] == "application/problem+json"
            assert response.json()["code"] == "FORBIDDEN"
            assert response.headers["X-Request-ID"] == response.json()["request_id"]
        finally:
            env.undo()
            get_settings.cache_clear()
            importlib.reload(main)
