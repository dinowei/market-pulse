from __future__ import annotations

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
from app.watchlists.service import InMemoryWatchlistService

WATCHLIST_DEPENDENCY = routers.get_watchlist_service


def user(email: str) -> AuthUserResponse:
    return AuthUserResponse(id=str(uuid4()), email=email, status="ACTIVE")


def client_for(
    monkeypatch, owner: AuthUserResponse, service: InMemoryWatchlistService
) -> TestClient:
    app.dependency_overrides[WATCHLIST_DEPENDENCY] = lambda: service
    app.dependency_overrides[routers.get_current_user] = lambda: owner
    return TestClient(app)


def clear_auth_override() -> None:
    app.dependency_overrides.pop(routers.get_current_user, None)


def test_unauthenticated_watchlists_return_problem_details(monkeypatch) -> None:
    clear_auth_override()
    app.dependency_overrides.pop(WATCHLIST_DEPENDENCY, None)
    auth = AuthService(
        store=InMemoryAuthStore(), sessions=InMemorySessionStore(), limiter=InMemoryRateLimiter()
    )
    monkeypatch.setattr(routers, "get_auth_service", lambda: auth)
    response = TestClient(app).get("/api/v1/watchlists")
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "UNAUTHORIZED"


def test_owner_can_create_list_add_canonical_item_and_list_only_own_data(monkeypatch) -> None:
    service = InMemoryWatchlistService()
    owner_a = user("a@example.com")
    client_a = client_for(monkeypatch, owner_a, service)
    created = client_a.post("/api/v1/watchlists", json={"name": "Tecnologia"})
    assert created.status_code == 201
    watchlist_id = created.json()["id"]

    item = client_a.post(
        f"/api/v1/watchlists/{watchlist_id}/items",
        json={"canonical_id": "equity.br.b3.petr4"},
    )
    assert item.status_code == 201
    assert item.json()["canonical_id"] == "equity.br.b3.petr4"
    assert "price" not in item.text

    duplicate = client_a.post(
        f"/api/v1/watchlists/{watchlist_id}/items",
        json={"canonical_id": "equity.br.b3.petr4"},
    )
    assert duplicate.status_code in {200, 201}
    assert len(client_a.get("/api/v1/watchlists").json()["items"][0]["items"]) == 1

    owner_b = user("b@example.com")
    client_b = client_for(monkeypatch, owner_b, service)
    assert client_b.get("/api/v1/watchlists").json()["items"] == []
    assert client_b.get(f"/api/v1/watchlists/{watchlist_id}").status_code == 404
    assert (
        client_b.patch(
            f"/api/v1/watchlists/{watchlist_id}", json={"name": "vazamento"}
        ).status_code
        == 404
    )
    assert client_b.delete(f"/api/v1/watchlists/{watchlist_id}").status_code == 404


def test_reorder_remove_and_blocked_instrument_are_controlled(monkeypatch) -> None:
    service = InMemoryWatchlistService()
    owner = user("owner@example.com")
    client = client_for(monkeypatch, owner, service)
    watchlist_id = client.post("/api/v1/watchlists", json={"name": "Acompanhar"}).json()["id"]
    for canonical_id in ("equity.br.b3.petr4", "equity.us.nasdaq.aapl"):
        assert (
            client.post(
                f"/api/v1/watchlists/{watchlist_id}/items", json={"canonical_id": canonical_id}
            ).status_code
            == 201
        )

    reordered = client.patch(
        f"/api/v1/watchlists/{watchlist_id}/items/reorder",
        json={"canonical_ids": ["equity.us.nasdaq.aapl", "equity.br.b3.petr4"]},
    )
    assert reordered.status_code == 200
    assert [item["canonical_id"] for item in reordered.json()["items"]] == [
        "equity.us.nasdaq.aapl",
        "equity.br.b3.petr4",
    ]
    assert (
        client.delete(f"/api/v1/watchlists/{watchlist_id}/items/equity.br.b3.petr4").status_code
        == 204
    )
    blocked = client.post(
        f"/api/v1/watchlists/{watchlist_id}/items",
        json={"canonical_id": "crypto.global.btc-usd"},
    )
    assert blocked.status_code == 422
    assert blocked.json()["code"] == "VALIDATION_ERROR"


def test_favorites_create_and_reuse_system_watchlist(monkeypatch) -> None:
    service = InMemoryWatchlistService()
    owner = user("owner@example.com")
    client = client_for(monkeypatch, owner, service)
    first = client.post("/api/v1/watchlists/favorites/equity.br.b3.petr4")
    second = client.post("/api/v1/watchlists/favorites/equity.br.b3.petr4")
    assert first.status_code == 201
    assert second.status_code in {200, 201}
    listed = client.get("/api/v1/watchlists").json()["items"]
    assert listed[0]["is_system"] is True
    assert len(listed) == 1
    assert len(listed[0]["items"]) == 1


def test_public_market_data_stays_public() -> None:
    clear_auth_override()
    assert TestClient(app).get("/api/v1/market-data/quotes/equity.br.b3.petr4").status_code == 200
