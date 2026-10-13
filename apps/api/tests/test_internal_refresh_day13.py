from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

import app.market_data.refresh_application as refresh_application
import app.routers as routers
from app.core.config import Settings
from app.main import app
from app.market_data.refresh import RefreshResult, RefreshStatus
from app.market_data.refresh_application import RefreshBatchRequest, RefreshMode
from app.providers.models import ProviderCapability


def payload(*ids: str, mode: str = "DEMO_ONLY") -> dict[str, object]:
    return {
        "dataset": "demo-quotes",
        "capability": "latest_quote",
        "canonical_ids": list(ids),
        "mode": mode,
    }


def configured(monkeypatch, secret: str = "local_demo_only_change_me") -> None:
    monkeypatch.setattr(
        routers,
        "get_settings",
        lambda: Settings(internal_refresh_secret=secret, refresh_max_items=3),
    )


def test_internal_refresh_fails_closed_without_or_with_wrong_secret(monkeypatch):
    configured(monkeypatch)
    client = TestClient(app)
    for headers in ({}, {"X-Cron-Secret": "wrong"}, {"Authorization": "Bearer user"}):
        response = client.post(
            "/api/v1/internal/refresh-quotes",
            json=payload("equity.br.b3.petr4"),
            headers=headers,
        )
        assert response.status_code == 401
        assert response.headers["content-type"].startswith("application/problem+json")
        assert "local_demo_only_change_me" not in response.text
        assert "Traceback" not in response.text


def test_user_cookie_does_not_authorize_internal_refresh(monkeypatch):
    configured(monkeypatch)
    response = TestClient(app).post(
        "/api/v1/internal/refresh-quotes",
        json=payload("equity.br.b3.petr4"),
        cookies={"session": "user-session"},
    )
    assert response.status_code == 401


def test_correct_secret_uses_constant_time_compare_and_returns_run_summary(monkeypatch):
    configured(monkeypatch)
    calls: list[tuple[str, str]] = []
    original = routers.secrets.compare_digest

    def compare(left: str, right: str) -> bool:
        calls.append((left, right))
        return original(left, right)

    monkeypatch.setattr(routers.secrets, "compare_digest", compare)
    monkeypatch.setattr(
        routers,
        "refresh_market_data",
        lambda **_: {
            "run_id": str(uuid4()),
            "status": "SUCCESS",
            "started_at": datetime.now(timezone.utc),
            "finished_at": datetime.now(timezone.utc),
            "total_items": 1,
            "succeeded_items": 1,
            "failed_items": 0,
            "skipped_items": 0,
            "quarantined_items": 0,
            "cache_invalidated_items": 1,
            "data_level": "DEMO",
            "warnings": [],
            "request_id": str(uuid4()),
        },
    )
    response = TestClient(app).post(
        "/api/v1/internal/refresh-quotes",
        json=payload("equity.br.b3.petr4"),
        headers={"X-Cron-Secret": "local_demo_only_change_me", "X-Request-ID": str(uuid4())},
    )
    assert response.status_code == 200
    assert response.json()["run_id"]
    assert calls == [("local_demo_only_change_me", "local_demo_only_change_me")]


def test_correct_secret_runs_demo_only_without_real_provider(monkeypatch):
    configured(monkeypatch)
    response = TestClient(app).post(
        "/api/v1/internal/refresh-quotes",
        json=payload("equity.br.b3.day13-demo"),
        headers={"X-Cron-Secret": "local_demo_only_change_me"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SUCCESS"
    assert body["data_level"] == "DEMO"
    assert body["succeeded_items"] == 1


def test_internal_refresh_rejects_extra_fields_empty_lists_and_oversized_batches(monkeypatch):
    configured(monkeypatch)
    client = TestClient(app)
    headers = {"X-Cron-Secret": "local_demo_only_change_me"}
    extra = {**payload("equity.br.b3.petr4"), "unexpected": True}
    assert (
        client.post("/api/v1/internal/refresh-quotes", json=extra, headers=headers).status_code
        == 422
    )
    assert (
        client.post("/api/v1/internal/refresh-quotes", json=payload(), headers=headers).status_code
        == 422
    )
    too_many = payload("a", "b", "c", "d")
    assert (
        client.post("/api/v1/internal/refresh-quotes", json=too_many, headers=headers).status_code
        == 422
    )


def test_refresh_secret_missing_from_configuration_fails_closed(monkeypatch):
    configured(monkeypatch, secret=None)
    response = TestClient(app).post(
        "/api/v1/internal/refresh-quotes",
        json=payload("equity.br.b3.petr4"),
        headers={"X-Cron-Secret": "anything"},
    )
    assert response.status_code in (401, 503)


def test_batch_failure_is_counted_without_aborting_other_items(monkeypatch):
    class PartialService:
        def refresh(self, request):
            if request.canonical_id.endswith("-bad"):
                return RefreshResult(RefreshStatus.FAILED, "bad", "bad", "key", "REFRESH_FAILED")
            return RefreshResult(RefreshStatus.SUCCESS, "ok", "ok", "key")

    monkeypatch.setattr(refresh_application, "_DEMO_SERVICE", PartialService())
    result = refresh_application.refresh_market_data(
        payload=RefreshBatchRequest(
            dataset="demo-quotes",
            capability=ProviderCapability.LATEST_QUOTE,
            canonical_ids=["equity.br.b3.good", "equity.br.b3-bad"],
            mode=RefreshMode.DEMO_ONLY,
        ),
        settings=Settings(environment="local", refresh_max_items=3),
        request_id=str(uuid4()),
    )
    assert result.status == "PARTIAL"
    assert result.succeeded_items == 1
    assert result.failed_items == 1
