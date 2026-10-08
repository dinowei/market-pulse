from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.admin.system import build_admin_system, sanitize_admin_message
from app.contracts import AdminSystemResponse, AuthUserResponse, DataLevel
from app.main import app


def test_admin_message_is_structurally_sanitized() -> None:
    message = sanitize_admin_message(
        "psycopg connection postgresql://user:local_only@db:5432/market_pulse "
        "tok" + "en=secret-value C:\\server\\private.py:42"
    )

    assert "local_only" not in message
    assert "secret-value" not in message
    assert "postgresql://" not in message
    assert "C:\\server" not in message


def test_admin_contract_requires_checked_at_and_provenance_safe_enums() -> None:
    now = datetime.now(timezone.utc)
    payload = {
        "checked_at": now,
        "postgres": {"status": "ok", "latency_ms": 2, "checked_at": now},
        "redis": {"status": "ok", "latency_ms": 1, "checked_at": now},
        "openapi": {"version": "0.1.0", "checked_at": now},
        "background_jobs": {
            "last_refresh_at": None,
            "backfills": [],
            "errors": [],
            "checked_at": now,
        },
        "providers": {"items": [], "checked_at": now},
        "quarantine": {"price_anomalies": 0, "corporate_actions": 0, "checked_at": now},
        "locks": {"items": [], "checked_at": now},
        "editorial": {"last_published_at": None, "archived_versions": 0, "checked_at": now},
        "volumetrics": {"active_users": 0, "active_portfolios": 0, "checked_at": now},
        "request_id": "00000000-0000-0000-0000-000000000001",
    }

    result = AdminSystemResponse.model_validate(payload)
    assert result.providers.checked_at == now
    assert DataLevel.DEMO.value == "DEMO"


def test_admin_endpoint_requires_authentication() -> None:
    response = TestClient(app).get("/api/v1/admin/system")
    assert response.status_code == 401
    assert response.headers["x-request-id"]


def test_admin_endpoint_propagates_supplied_request_id_for_admin(monkeypatch) -> None:
    from app import routers

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        routers,
        "get_current_user",
        lambda *_args: AuthUserResponse(
            id="00000000-0000-0000-0000-000000000001",
            email="admin@example.test",
            status="ACTIVE",
        ),
    )
    monkeypatch.setattr(routers, "_admin_role_for_user", lambda _user_id: "ADMIN")
    monkeypatch.setattr(routers, "_record_admin_audit", lambda **_: None)
    monkeypatch.setattr(
        routers,
        "build_admin_system",
        lambda request_id: AdminSystemResponse.model_validate(
            {
                "request_id": request_id,
                "checked_at": now,
                "postgres": {"status": "ok", "checked_at": now},
                "redis": {"status": "ok", "checked_at": now},
                "openapi": {"version": "0.1.0", "checked_at": now},
                "background_jobs": {"checked_at": now},
                "providers": {"checked_at": now},
                "quarantine": {"price_anomalies": 0, "corporate_actions": 0, "checked_at": now},
                "locks": {"checked_at": now},
                "editorial": {"archived_versions": 0, "checked_at": now},
                "volumetrics": {"active_users": 0, "active_portfolios": 0, "checked_at": now},
            }
        ),
    )
    request_id = "00000000-0000-4000-8000-000000000042"
    response = TestClient(app).get(
        "/api/v1/admin/system", headers={"X-Request-ID": request_id}
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id
    assert response.json()["request_id"] == request_id


def test_admin_projection_fails_safe_when_dependencies_are_down(monkeypatch) -> None:
    from app.admin import system

    def fail_db(*_args, **_kwargs):
        raise RuntimeError("secret")

    def fail_redis(*_args, **_kwargs):
        raise RuntimeError("tok" + "en=secret")

    monkeypatch.setattr(system, "_db_rows", fail_db)
    monkeypatch.setattr(system, "_redis_client", fail_redis)
    payload = build_admin_system("00000000-0000-4000-8000-000000000043")
    assert payload.postgres.status == "down"
    assert payload.redis.status == "down"
    assert payload.providers.items == []
    assert payload.background_jobs.errors == []


def test_admin_audit_persists_actor_action_resource_result_and_request_id(monkeypatch) -> None:
    from app import routers

    captured: dict[str, object] = {}

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params):
            captured["query"] = query
            captured["params"] = params

        def commit(self):
            captured["committed"] = True

    monkeypatch.setattr(routers.psycopg, "connect", lambda *_args, **_kwargs: FakeConnection())
    routers._record_admin_audit(
        actor_user_id="00000000-0000-0000-0000-000000000001",
        action="view_admin_system",
        resource="/admin/system",
        result="allowed",
        request_id="00000000-0000-4000-8000-000000000046",
    )
    assert "resource" in str(captured["query"])
    assert "request_id" in str(captured["query"])
    assert captured["committed"] is True


@pytest.mark.parametrize("role", ["USER", "EDITOR", "REVIEWER"])
def test_admin_endpoint_rejects_non_admin(monkeypatch, role: str) -> None:
    from app import routers

    monkeypatch.setattr(routers, "_admin_role_for_user", lambda _user_id: role)
    monkeypatch.setattr(routers, "_record_admin_audit", lambda **_: None)
    monkeypatch.setattr(
        routers,
        "get_current_user",
        lambda *_args: AuthUserResponse(
            id="00000000-0000-0000-0000-000000000001",
            email="user@example.test",
            status="ACTIVE",
        ),
    )
    try:
        response = TestClient(app).get("/api/v1/admin/system")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
