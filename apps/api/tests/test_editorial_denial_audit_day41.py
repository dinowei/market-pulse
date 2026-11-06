"""Day 41: refused editorial attempts leave an audit row without payload or personal data."""

import json

import pytest
from fastapi.testclient import TestClient

import app.routers as routers
from app.contracts import AuthUserResponse
from app.editorial.service import InMemoryEditorialService
from app.main import app

USER = AuthUserResponse(
    id="00000000-0000-0000-0000-0000000000aa", email="u@example.invalid", status="ACTIVE"
)


class _Connection:
    def __init__(self, calls: list, fail: bool) -> None:
        self.calls, self.fail = calls, fail

    def __enter__(self):
        if self.fail:
            raise ConnectionError("database down")
        return self

    def __exit__(self, *exc) -> None:
        return None

    def execute(self, sql: str, params: tuple) -> None:
        self.calls.append((sql, params))

    def commit(self) -> None:
        return None


@pytest.fixture
def as_role():
    def use(role: str) -> TestClient:
        app.dependency_overrides[routers.get_editorial_service] = InMemoryEditorialService
        app.dependency_overrides[routers.get_current_user] = lambda: USER
        app.dependency_overrides[routers.get_editorial_role] = lambda: role
        return TestClient(app)

    yield use
    for dependency in (
        routers.get_editorial_service,
        routers.get_current_user,
        routers.get_editorial_role,
    ):
        app.dependency_overrides.pop(dependency, None)


def test_a_refused_attempt_is_audited_with_role_and_route_only(monkeypatch, as_role) -> None:
    calls: list = []
    monkeypatch.setattr(routers.psycopg, "connect", lambda *a, **k: _Connection(calls, fail=False))
    body = {"slug": "secret-draft", "title": "Rascunho", "blocks": []}
    response = as_role("USER").post("/api/v1/editorial/admin/posts", json=body)
    assert response.status_code == 403
    ((sql, params),) = calls
    assert "INSERT INTO audit_logs" in sql and "'DENIED'" in sql
    action, actor, metadata, request_id = params
    assert (action, actor) == ("editorial_permission_denied", USER.id)
    assert json.loads(metadata) == {
        "role": "USER",
        "method": "POST",
        "route": "/api/v1/editorial/admin/posts",
    }
    assert "secret-draft" not in sql + str(params), "the payload never reaches the audit row"
    assert USER.email not in str(params)
    assert request_id


def test_an_audit_failure_still_returns_403(monkeypatch, as_role) -> None:
    monkeypatch.setattr(routers.psycopg, "connect", lambda *a, **k: _Connection([], fail=True))
    assert as_role("USER").get("/api/v1/editorial/admin/posts").status_code == 403


def test_an_allowed_role_writes_no_denial(monkeypatch, as_role) -> None:
    calls: list = []
    monkeypatch.setattr(routers.psycopg, "connect", lambda *a, **k: _Connection(calls, fail=False))
    assert as_role("EDITOR").get("/api/v1/editorial/admin/posts").status_code == 200
    assert calls == []
