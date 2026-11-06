"""Day 41: portfolio drawdown on a cash-flow-neutral equity curve."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

import app.portfolios.performance as performance_module
from app.contracts import (
    EquityCurvePointResponse,
    EquityCurveResponse,
    PortfolioCreateRequest,
    PortfolioEventRequest,
)
from app.core.config import Settings
from app.portfolios.performance import PortfolioPerformanceService, calculate_drawdown
from app.portfolios.service import InMemoryPortfolioService

OWNER = "owner-drawdown"


def test_drawdown_is_measured_from_the_running_peak_in_decimal() -> None:
    values = [
        (date(2026, 1, 5), Decimal("100")),
        (date(2026, 1, 6), Decimal("120")),
        (date(2026, 1, 7), Decimal("90")),
        (date(2026, 1, 8), Decimal("130")),
    ]
    points = calculate_drawdown(values)
    assert [point.peak_value_base for point in points] == [
        Decimal(v) for v in ("100", "120", "120", "130")
    ]
    assert [point.drawdown for point in points] == [
        Decimal("0"),
        Decimal("0"),
        Decimal("-0.25"),
        Decimal("0"),
    ]
    with pytest.raises(ValueError):
        calculate_drawdown([(date(2026, 1, 5), Decimal("0"))])


def _service(*events: tuple[str, str, datetime]) -> tuple[PortfolioPerformanceService, str]:
    portfolios = InMemoryPortfolioService()
    created = portfolios.create(OWNER, PortfolioCreateRequest(name="DD", base_currency="BRL"))
    for index, (kind, amount, when) in enumerate(events):
        portfolios.add_event(
            OWNER,
            created.id,
            PortfolioEventRequest(
                event_type=kind, currency="BRL", gross_amount=Decimal(amount), occurred_at=when
            ),
            f"dd-{index}",
            f"req-{index}",
        )
    return PortfolioPerformanceService(portfolios), created.id


def _curve(portfolio_id: str, *values: str, status: str = "COMPLETE") -> EquityCurveResponse:
    return EquityCurveResponse(
        portfolio_id=portfolio_id,
        base_currency="BRL",
        methodology="test",
        points=[
            EquityCurvePointResponse(
                valuation_date=date(2026, 1, 5 + offset),
                total_value_base=Decimal(value),
                cash_value_base=Decimal(value),
                positions_value_base=Decimal("0"),
                data_level="DEMO",
                freshness="STALE",
                valuation_status=status,
            )
            for offset, value in enumerate(values)
        ],
    )


def _demo(monkeypatch) -> None:
    settings = Settings(demo_enabled=True)
    monkeypatch.setattr(performance_module, "get_settings", lambda: settings)


START = datetime(2026, 1, 5, 12, tzinfo=UTC)


def test_without_a_valuation_history_the_drawdown_is_unavailable() -> None:
    service, portfolio_id = _service(("CASH_DEPOSIT", "100", START))
    body = service.drawdown_response(OWNER, portfolio_id)
    assert (body.status, body.missing_inputs, body.points) == (
        "UNAVAILABLE",
        ("HISTORICAL_VALUATION",),
        [],
    )


def test_complete_neutral_curve_reports_peak_trough_and_maximum(monkeypatch) -> None:
    _demo(monkeypatch)
    service, portfolio_id = _service(("CASH_DEPOSIT", "100", START))
    monkeypatch.setattr(
        service, "equity_curve_response", lambda *_: _curve(portfolio_id, "100", "120", "90", "130")
    )
    body = service.drawdown_response(OWNER, portfolio_id)
    assert body.status == "COMPLETE"
    assert body.max_drawdown == Decimal("-0.25")
    assert (body.peak_date, body.trough_date) == (date(2026, 1, 6), date(2026, 1, 7))


def test_a_withdrawal_after_the_start_is_never_read_as_a_loss(monkeypatch) -> None:
    _demo(monkeypatch)
    later = datetime(2026, 1, 7, 12, tzinfo=UTC)
    service, portfolio_id = _service(
        ("CASH_DEPOSIT", "100", START), ("CASH_WITHDRAWAL", "30", later)
    )
    monkeypatch.setattr(
        service, "equity_curve_response", lambda *_: _curve(portfolio_id, "100", "100", "70")
    )
    body = service.drawdown_response(OWNER, portfolio_id)
    assert (body.status, body.missing_inputs, body.max_drawdown) == (
        "UNAVAILABLE",
        ("EXTERNAL_FLOWS_AFTER_START",),
        None,
    )


def test_incomplete_valuations_keep_the_drawdown_unavailable(monkeypatch) -> None:
    _demo(monkeypatch)
    service, portfolio_id = _service(("CASH_DEPOSIT", "100", START))
    monkeypatch.setattr(
        service,
        "equity_curve_response",
        lambda *_: _curve(portfolio_id, "100", "90", status="PARTIAL"),
    )
    assert service.drawdown_response(OWNER, portfolio_id).missing_inputs == (
        "HISTORICAL_VALUATION",
    )


def test_a_flat_curve_has_zero_drawdown_and_no_trough(monkeypatch) -> None:
    _demo(monkeypatch)
    service, portfolio_id = _service(("CASH_DEPOSIT", "100", START))
    monkeypatch.setattr(
        service, "equity_curve_response", lambda *_: _curve(portfolio_id, "100", "100")
    )
    body = service.drawdown_response(OWNER, portfolio_id)
    assert (body.max_drawdown, body.peak_date, body.trough_date) == (Decimal("0"), None, None)
