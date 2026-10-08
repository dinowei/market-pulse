"""H-21: GET /portfolios/{id}/overview equals the eight separate endpoints in one request."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import app.routers as routers
from app.contracts import (
    AuthUserResponse,
    PortfolioCreateRequest,
    PortfolioEventMarkersResponse,
    PortfolioEventRequest,
)
from app.main import app
from app.portfolios.day27 import PortfolioReadModelNotFound
from app.portfolios.performance import PortfolioPerformanceService
from app.portfolios.service import InMemoryPortfolioService

OWNER = AuthUserResponse(id="owner-overview", email="o@example.invalid", status="ACTIVE")
OTHER = AuthUserResponse(id="other-overview", email="x@example.invalid", status="ACTIVE")
PARTS = {
    "summary": "summary",
    "events": "events",
    "valuation": "valuation",
    "performance": "performance",
    "equity_curve": "equity-curve",
    "decomposition": "performance/decomposition",
    "income": "income",
    "event_markers": "event-markers",
}


class _ReadModels:
    """Postgres-free stand-in for the Day 27 read models, with the same ownership rule."""

    def __init__(self, portfolios: InMemoryPortfolioService) -> None:
        self.portfolios = portfolios

    def _own(self, user_id: str, portfolio_id: str) -> None:
        if not any(item.id == portfolio_id for item in self.portfolios.list(user_id).items):
            raise PortfolioReadModelNotFound

    def income(self, user_id: str, portfolio_id: str) -> list:
        self._own(user_id, portfolio_id)
        return []

    def markers(self, user_id: str, portfolio_id: str) -> PortfolioEventMarkersResponse:
        self._own(user_id, portfolio_id)
        return PortfolioEventMarkersResponse(portfolio_id=portfolio_id, items=[])


@pytest.fixture
def portfolio_id():
    portfolios = InMemoryPortfolioService()
    created = portfolios.create(
        OWNER.id, PortfolioCreateRequest(name="Overview", base_currency="BRL")
    )
    portfolios.add_event(
        OWNER.id,
        created.id,
        PortfolioEventRequest(
            event_type="CASH_DEPOSIT",
            currency="BRL",
            gross_amount=Decimal("1000.00"),
            occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
        "overview-deposit",
        "req-overview",
    )
    performance = PortfolioPerformanceService(portfolios)
    read_models = _ReadModels(portfolios)
    app.dependency_overrides[routers.get_portfolio_service] = lambda: portfolios
    app.dependency_overrides[routers.get_portfolio_performance_service] = lambda: performance
    app.dependency_overrides[routers.get_portfolio_day27_service] = lambda: read_models
    yield created.id
    for dependency in (
        routers.get_portfolio_service,
        routers.get_portfolio_performance_service,
        routers.get_portfolio_day27_service,
        routers.get_current_user,
    ):
        app.dependency_overrides.pop(dependency, None)


def _without_clock(value):
    # as_of is the computation instant, so two separate requests legitimately differ there.
    if isinstance(value, dict):
        return {key: _without_clock(item) for key, item in value.items() if key != "as_of"}
    if isinstance(value, list):
        return [_without_clock(item) for item in value]
    return value


def test_overview_matches_each_separate_endpoint(portfolio_id: str) -> None:
    app.dependency_overrides[routers.get_current_user] = lambda: OWNER
    client = TestClient(app)
    overview = client.get(f"/api/v1/portfolios/{portfolio_id}/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert set(body) == set(PARTS)
    for field, path in PARTS.items():
        separate = client.get(f"/api/v1/portfolios/{portfolio_id}/{path}")
        assert separate.status_code == 200, path
        assert _without_clock(body[field]) == _without_clock(separate.json()), field
    assert body["summary"]["portfolio_id"] == portfolio_id
    assert len(body["events"]) == 1 and body["events"][0]["event_type"] == "CASH_DEPOSIT"


def test_overview_keeps_owner_isolation_and_requires_a_session(portfolio_id: str) -> None:
    app.dependency_overrides[routers.get_current_user] = lambda: OTHER
    assert TestClient(app).get(f"/api/v1/portfolios/{portfolio_id}/overview").status_code == 404
    app.dependency_overrides.pop(routers.get_current_user, None)
    assert TestClient(app).get(f"/api/v1/portfolios/{portfolio_id}/overview").status_code == 401
