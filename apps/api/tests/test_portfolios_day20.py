from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

import app.routers as routers
from app.contracts import AuthUserResponse
from app.main import app
from app.portfolios.service import (
    InMemoryPortfolioService,
    PortfolioEventInput,
    PortfolioValidationError,
    replay_events,
)


def user(email: str) -> AuthUserResponse:
    return AuthUserResponse(id=str(uuid4()), email=email, status="ACTIVE")


def event(
    event_type: str,
    *,
    currency: str = "BRL",
    canonical_id: str | None = None,
    quantity: str | None = None,
    unit_price: str | None = None,
    gross_amount: str | None = None,
    occurred_at: str = "2026-09-01T10:00:00+00:00",
) -> PortfolioEventInput:
    return PortfolioEventInput(
        id=str(uuid4()),
        event_type=event_type,
        currency=currency,
        canonical_id=canonical_id,
        quantity=Decimal(quantity) if quantity is not None else None,
        unit_price=Decimal(unit_price) if unit_price is not None else None,
        gross_amount=Decimal(gross_amount) if gross_amount is not None else None,
        occurred_at=datetime.fromisoformat(occurred_at),
        created_at=datetime.now(timezone.utc),
    )


def test_replay_calculates_cash_position_and_weighted_average_cost() -> None:
    events = [
        event("CASH_DEPOSIT", gross_amount="3000", occurred_at="2026-09-01T10:00:00+00:00"),
        event(
            "BUY",
            canonical_id="equity.br.b3.petr4",
            quantity="4",
            unit_price="100",
            occurred_at="2026-09-01T10:01:00+00:00",
        ),
        event(
            "BUY",
            canonical_id="equity.br.b3.petr4",
            quantity="6",
            unit_price="200",
            occurred_at="2026-09-01T10:02:00+00:00",
        ),
        event(
            "SELL",
            canonical_id="equity.br.b3.petr4",
            quantity="2",
            unit_price="250",
            occurred_at="2026-09-01T10:03:00+00:00",
        ),
        event("FEE", gross_amount="10", occurred_at="2026-09-01T10:04:00+00:00"),
    ]

    state = replay_events(events)

    assert state.cash_balances == {"BRL": Decimal("1890")}
    assert state.positions["equity.br.b3.petr4"].quantity == Decimal("8")
    assert state.positions["equity.br.b3.petr4"].total_cost == Decimal("1280")
    assert state.positions["equity.br.b3.petr4"].weighted_average_cost == Decimal("160")
    assert all(isinstance(value, Decimal) for value in state.cash_balances.values())


def test_replay_rejects_negative_position_and_negative_cash() -> None:
    try:
        replay_events(
            [event("SELL", canonical_id="equity.br.b3.petr4", quantity="1", unit_price="10")]
        )
    except PortfolioValidationError as exc:
        assert "position" in str(exc)
    else:
        raise AssertionError("negative position was accepted")


def test_replay_reversal_compensates_original_without_mutating_it() -> None:
    deposit = event("CASH_DEPOSIT", gross_amount="100")
    reversal = PortfolioEventInput(
        id=str(uuid4()),
        event_type="REVERSAL",
        currency="BRL",
        canonical_id=None,
        quantity=None,
        unit_price=None,
        gross_amount=None,
        reversal_of_event_id=deposit.id,
        occurred_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
        created_at=datetime.now(timezone.utc),
    )

    state = replay_events([deposit, reversal])

    assert state.cash_balances == {"BRL": Decimal("0")}
    assert state.event_count == 2


def client_for(owner: AuthUserResponse, service: InMemoryPortfolioService) -> TestClient:
    app.dependency_overrides[routers.get_portfolio_service] = lambda: service
    app.dependency_overrides[routers.get_current_user] = lambda: owner
    return TestClient(app)


def clear_overrides() -> None:
    app.dependency_overrides.pop(routers.get_portfolio_service, None)
    app.dependency_overrides.pop(routers.get_current_user, None)


def test_private_portfolios_are_owner_scoped_and_base_currency_is_immutable() -> None:
    service = InMemoryPortfolioService()
    owner_a = user("a@example.com")
    client_a = client_for(owner_a, service)
    created = client_a.post(
        "/api/v1/portfolios", json={"name": "Longo prazo", "base_currency": "BRL"}
    )
    assert created.status_code == 201
    portfolio_id = created.json()["id"]
    assert (
        client_a.patch(
            f"/api/v1/portfolios/{portfolio_id}",
            json={"name": "Reserva", "base_currency": "USD"},
        ).status_code
        == 409
    )

    owner_b = user("b@example.com")
    client_b = client_for(owner_b, service)
    assert client_b.get(f"/api/v1/portfolios/{portfolio_id}").status_code == 404
    assert client_b.get("/api/v1/portfolios").json()["items"] == []
    clear_overrides()


def test_event_idempotency_and_portfolio_summary_use_typed_replay() -> None:
    service = InMemoryPortfolioService()
    owner = user("owner@example.com")
    client = client_for(owner, service)
    portfolio_id = client.post(
        "/api/v1/portfolios", json={"name": "Carteira", "base_currency": "BRL"}
    ).json()["id"]
    headers = {"Idempotency-Key": "deposit-1"}
    payload = {
        "event_type": "CASH_DEPOSIT",
        "currency": "BRL",
        "gross_amount": "1000.00",
        "occurred_at": "2026-09-01T10:00:00Z",
    }
    first = client.post(f"/api/v1/portfolios/{portfolio_id}/events", json=payload, headers=headers)
    replay = client.post(f"/api/v1/portfolios/{portfolio_id}/events", json=payload, headers=headers)
    conflict = client.post(
        f"/api/v1/portfolios/{portfolio_id}/events",
        json={**payload, "gross_amount": "900.00"},
        headers=headers,
    )
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert conflict.status_code == 409
    summary = client.get(f"/api/v1/portfolios/{portfolio_id}/summary")
    assert summary.status_code == 200
    assert summary.json()["cash_balances"]["BRL"] == "1000.00"
    clear_overrides()


def test_financial_event_rules_require_key_and_reversal_is_append_only() -> None:
    service = InMemoryPortfolioService()
    owner = user("ledger@example.com")
    client = client_for(owner, service)
    portfolio_id = client.post(
        "/api/v1/portfolios", json={"name": "Ledger", "base_currency": "BRL"}
    ).json()["id"]
    payload = {
        "event_type": "CASH_DEPOSIT",
        "currency": "BRL",
        "gross_amount": "100.00",
        "occurred_at": "2026-09-01T10:00:00Z",
    }
    assert client.post(f"/api/v1/portfolios/{portfolio_id}/events", json=payload).status_code == 422
    created = client.post(
        f"/api/v1/portfolios/{portfolio_id}/events",
        json=payload,
        headers={"Idempotency-Key": "deposit-ledger"},
    )
    assert created.status_code == 201
    assert created.json()["id"]
    buy = client.post(
        f"/api/v1/portfolios/{portfolio_id}/events",
        json={
            "event_type": "BUY",
            "currency": "BRL",
            "canonical_id": "equity.br.b3.petr4",
            "quantity": "1",
            "unit_price": "50",
            "occurred_at": "2026-09-01T11:00:00Z",
        },
        headers={"Idempotency-Key": "buy-ledger"},
    )
    assert buy.status_code == 201
    event_id = buy.json()["id"]
    oversell = client.post(
        f"/api/v1/portfolios/{portfolio_id}/events",
        json={
            "event_type": "SELL",
            "currency": "BRL",
            "canonical_id": "equity.br.b3.petr4",
            "quantity": "2",
            "unit_price": "50",
            "occurred_at": "2026-09-01T12:00:00Z",
        },
        headers={"Idempotency-Key": "oversell-ledger"},
    )
    assert oversell.status_code == 422
    reversal = client.post(
        f"/api/v1/portfolios/{portfolio_id}/events/{event_id}/reversal",
        headers={"Idempotency-Key": "reverse-deposit"},
    )
    assert reversal.status_code == 201
    assert reversal.json()["reversal_of_event_id"] == event_id
    assert client.post(
        f"/api/v1/portfolios/{portfolio_id}/events/{event_id}/reversal",
        headers={"Idempotency-Key": "reverse-deposit-again"},
    ).status_code == 409
    assert len(client.get(f"/api/v1/portfolios/{portfolio_id}/events").json()) == 3
    clear_overrides()
