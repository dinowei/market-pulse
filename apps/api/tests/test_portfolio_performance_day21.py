from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import app.routers as routers
from app.contracts import AuthUserResponse, PortfolioCreateRequest
from app.main import app
from app.portfolios.performance import (
    FxMark,
    PerformanceStatus,
    PortfolioPerformanceService,
    PriceMark,
    TWRPoint,
    calculate_twr,
    calculate_valuation,
)
from app.portfolios.service import InMemoryPortfolioService, PortfolioEventInput

UTC = timezone.utc


def event(
    event_id: str,
    event_type: str,
    day: int,
    *,
    currency: str = "BRL",
    canonical_id: str | None = None,
    quantity: str | None = None,
    unit_price: str | None = None,
    gross_amount: str | None = None,
    fee_amount: str | None = None,
) -> PortfolioEventInput:
    occurred = datetime(2026, 1, day, tzinfo=UTC)
    return PortfolioEventInput(
        id=event_id,
        event_type=event_type,
        currency=currency,
        canonical_id=canonical_id,
        quantity=Decimal(quantity) if quantity else None,
        unit_price=Decimal(unit_price) if unit_price else None,
        gross_amount=Decimal(gross_amount) if gross_amount else None,
        fee_amount=Decimal(fee_amount) if fee_amount else None,
        occurred_at=occurred,
        created_at=occurred,
    )


def mark(value: str, currency: str = "BRL") -> PriceMark:
    captured = datetime(2026, 1, 31, tzinfo=UTC)
    return PriceMark(
        canonical_id="equity.br.b3.petr4",
        value=Decimal(value),
        currency=currency,
        provider="demo",
        dataset="demo-portfolio-marks",
        data_level="DEMO",
        freshness="STALE",
        source_timestamp=captured,
        collected_at=captured,
        limitations=("Marca sintética local; não representa mercado real.",),
    )


def test_valuation_and_pnl_use_remaining_cost_and_decimal() -> None:
    events = [
        event("deposit", "CASH_DEPOSIT", 1, gross_amount="1000"),
        event(
            "buy",
            "BUY",
            2,
            canonical_id="equity.br.b3.petr4",
            quantity="10",
            unit_price="50",
            gross_amount="500",
        ),
        event(
            "sell",
            "SELL",
            3,
            canonical_id="equity.br.b3.petr4",
            quantity="4",
            unit_price="70",
            gross_amount="280",
        ),
    ]
    result = calculate_valuation(
        events,
        base_currency="BRL",
        prices={"equity.br.b3.petr4": mark("60")},
        fx_rates={},
    )
    assert result.status is PerformanceStatus.COMPLETE
    assert result.total_value_base == Decimal("1140")
    assert result.realized_pnl == Decimal("80")
    assert result.unrealized_pnl == Decimal("60")
    assert result.positions[0].remaining_cost_basis == Decimal("300")
    assert result.positions[0].weighted_average_cost == Decimal("50")


def test_missing_fx_is_partial_and_never_invented() -> None:
    events = [
        event("deposit", "CASH_DEPOSIT", 1, gross_amount="1000", currency="USD"),
        event(
            "buy",
            "BUY",
            2,
            currency="USD",
            canonical_id="equity.us.nasdaq.aapl",
            quantity="2",
            unit_price="100",
            gross_amount="200",
        ),
    ]
    usd_mark = PriceMark(**{**mark("120", "USD").__dict__, "canonical_id": "equity.us.nasdaq.aapl"})
    result = calculate_valuation(
        events,
        base_currency="BRL",
        prices={"equity.us.nasdaq.aapl": usd_mark},
        fx_rates={},
    )
    assert result.status is PerformanceStatus.PARTIAL
    assert result.total_value_base is None
    assert "FX_USD_BRL" in result.missing_inputs


def test_explicit_fx_direction_converts_native_value() -> None:
    events = [
        event("deposit", "CASH_DEPOSIT", 1, gross_amount="1000", currency="USD"),
        event(
            "buy",
            "BUY",
            2,
            currency="USD",
            canonical_id="equity.us.nasdaq.aapl",
            quantity="2",
            unit_price="100",
            gross_amount="200",
        ),
    ]
    usd_mark = PriceMark(**{**mark("120", "USD").__dict__, "canonical_id": "equity.us.nasdaq.aapl"})
    fx = FxMark(
        base_currency="USD",
        quote_currency="BRL",
        rate=Decimal("5"),
        provider="demo",
        dataset="demo-portfolio-fx",
        data_level="DEMO",
        freshness="STALE",
        source_timestamp=datetime(2026, 1, 31, tzinfo=UTC),
        collected_at=datetime(2026, 1, 31, tzinfo=UTC),
        limitations=("Taxa sintética local; não representa mercado real.",),
    )
    result = calculate_valuation(
        events,
        base_currency="BRL",
        prices={"equity.us.nasdaq.aapl": usd_mark},
        fx_rates={("USD", "BRL"): fx},
    )
    assert result.status is PerformanceStatus.COMPLETE
    assert result.total_value_base == Decimal("5200")
    assert result.positions[0].market_value_base == Decimal("1200")


def test_twr_removes_external_flow_from_return() -> None:
    points = [
        TWRPoint(datetime(2026, 1, 1, tzinfo=UTC), Decimal("100"), Decimal("0")),
        TWRPoint(datetime(2026, 1, 2, tzinfo=UTC), Decimal("120"), Decimal("0")),
        TWRPoint(datetime(2026, 1, 3, tzinfo=UTC), Decimal("220"), Decimal("100")),
    ]
    result = calculate_twr(points)
    assert result.status is PerformanceStatus.COMPLETE
    assert result.twr == Decimal("0.20")


def test_twr_requires_positive_beginning_value() -> None:
    with pytest.raises(ValueError, match="beginning value"):
        calculate_twr([TWRPoint(datetime(2026, 1, 1, tzinfo=UTC), Decimal("0"), Decimal("0"))])


def test_performance_routes_preserve_owner_isolation_and_401() -> None:
    service = InMemoryPortfolioService()
    owner_a = AuthUserResponse(id="owner-a", email="a@example.invalid", status="ACTIVE")
    owner_b = AuthUserResponse(id="owner-b", email="b@example.invalid", status="ACTIVE")
    portfolio = service.create(owner_a.id, PortfolioCreateRequest(name="A", base_currency="BRL"))
    performance = PortfolioPerformanceService(service)
    app.dependency_overrides[routers.get_portfolio_performance_service] = lambda: performance
    app.dependency_overrides[routers.get_current_user] = lambda: owner_b
    try:
        response = TestClient(app).get(f"/api/v1/portfolios/{portfolio.id}/valuation")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(routers.get_portfolio_performance_service, None)
        app.dependency_overrides.pop(routers.get_current_user, None)
    assert TestClient(app).get(f"/api/v1/portfolios/{portfolio.id}/valuation").status_code == 401
