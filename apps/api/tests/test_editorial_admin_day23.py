from datetime import date

from fastapi.testclient import TestClient

import app.routers as routers
from app.contracts import AuthUserResponse
from app.editorial.service import InMemoryEditorialService
from app.main import app


def _user() -> AuthUserResponse:
    return AuthUserResponse(id="editor-user", email="editor@example.invalid", status="ACTIVE")


def _override(service: InMemoryEditorialService, role: str):
    app.dependency_overrides[routers.get_editorial_service] = lambda: service
    app.dependency_overrides[routers.get_current_user] = _user
    app.dependency_overrides[routers.get_editorial_role] = lambda: role


def _clear() -> None:
    for dependency in (
        routers.get_editorial_service,
        routers.get_current_user,
        routers.get_editorial_role,
    ):
        app.dependency_overrides.pop(dependency, None)


def test_common_user_cannot_access_editorial_admin() -> None:
    service = InMemoryEditorialService()
    _override(service, "USER")
    try:
        response = TestClient(app).get("/api/v1/editorial/admin/posts")
        assert response.status_code == 403
        assert response.headers["content-type"].startswith("application/problem+json")
    finally:
        _clear()


def test_editor_reviewer_publish_flow_and_public_history() -> None:
    service = InMemoryEditorialService()
    _override(service, "EDITOR")
    client = TestClient(app)
    try:
        created = client.post(
            "/api/v1/editorial/admin/posts",
            json={
                "slug": "call-day23",
                "title": "Call",
                "content_date": str(date.today()),
                "blocks": [],
            },
        )
        assert created.status_code == 201
        post_id = created.json()["id"]
        assert (
            client.post(f"/api/v1/editorial/admin/posts/{post_id}/submit-review").status_code == 200
        )

        app.dependency_overrides[routers.get_editorial_role] = lambda: "REVIEWER"
        assert client.post(f"/api/v1/editorial/admin/posts/{post_id}/approve").status_code == 200
        assert client.post(f"/api/v1/editorial/admin/posts/{post_id}/publish").status_code == 200
        public = client.get("/api/v1/editorial/posts/call-day23/versions")
        assert public.status_code == 200
        assert [version["status"] for version in public.json()["items"]] == ["PUBLISHED"]
    finally:
        _clear()


def test_prescriptive_content_cannot_be_published_and_correction_is_new_version() -> None:
    service = InMemoryEditorialService()
    _override(service, "EDITOR")
    client = TestClient(app)
    try:
        created = client.post(
            "/api/v1/editorial/admin/posts",
            json={
                "slug": "call-validation",
                "title": "Call",
                "content_date": str(date.today()),
                "blocks": [
                    {
                        "content_type": "FACT",
                        "text": "Venda PETR4",
                        "sources": [{"label": "Fonte", "publisher": "Interna"}],
                    }
                ],
            },
        )
        post_id = created.json()["id"]
        client.post(f"/api/v1/editorial/admin/posts/{post_id}/submit-review")
        app.dependency_overrides[routers.get_editorial_role] = lambda: "REVIEWER"
        client.post(f"/api/v1/editorial/admin/posts/{post_id}/approve")
        failed = client.post(f"/api/v1/editorial/admin/posts/{post_id}/publish")
        assert failed.status_code == 422
        assert failed.headers["content-type"].startswith("application/problem+json")
    finally:
        _clear()
