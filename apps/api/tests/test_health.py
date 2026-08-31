from fastapi.testclient import TestClient

import app.main as main
from app.main import app


def test_health_returns_diagnostic_contract() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert body["environment"] == "local"
    assert body["timestamp"].endswith("+00:00")


def test_live_does_not_require_dependencies() -> None:
    response = TestClient(app).get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_reports_dependency_failure_without_secrets(monkeypatch) -> None:
    async def unavailable(_settings) -> bool:
        return False

    monkeypatch.setattr(main, "check_database", unavailable)
    monkeypatch.setattr(main, "check_cache", unavailable)
    response = TestClient(app).get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"] == {"database": "failed", "cache": "failed"}
    assert "market_pulse_local_only" not in response.text


def test_ready_reports_both_dependencies_healthy(monkeypatch) -> None:
    async def available(_settings) -> bool:
        return True

    monkeypatch.setattr(main, "check_database", available)
    monkeypatch.setattr(main, "check_cache", available)
    response = TestClient(app).get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
