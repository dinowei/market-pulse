from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_not_found_and_validation_use_problem_details() -> None:
    not_found = client.get("/api/v1/not-found")
    invalid = client.get("/api/v1/instruments?limit=101")

    assert not_found.status_code == 404
    assert invalid.status_code == 422
    for response in (not_found, invalid):
        body = response.json()
        assert (
            set(("type", "title", "status", "detail", "instance", "code", "request_id"))
            <= body.keys()
        )
        assert "Traceback" not in response.text


def test_request_id_is_preserved() -> None:
    request_id = str(uuid4())
    response = client.get("/health/live", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id


def test_unscoped_portfolio_events_endpoint_was_removed() -> None:
    # Historical /api/v1/portfolio-events had no auth dependency and duplicated
    # the owner-scoped, authenticated POST /api/v1/portfolios/{id}/events.
    # Guard against silently reintroducing it without Depends(get_current_user).
    response = client.post(
        "/api/v1/portfolio-events",
        json={"portfolio_id": "00000000-0000-0000-0000-000000000001"},
        headers={"Idempotency-Key": f"contract-{uuid4()}"},
    )
    assert response.status_code == 404


def test_portfolio_events_endpoint_requires_session() -> None:
    response = client.post(
        "/api/v1/portfolios/00000000-0000-0000-0000-000000000001/events",
        json={
            "event_type": "CASH_DEPOSIT",
            "event_date": "2026-08-31",
            "currency": "BRL",
            "cash_amount": "10.00",
        },
        headers={"Idempotency-Key": f"contract-{uuid4()}"},
    )
    assert response.status_code == 401
