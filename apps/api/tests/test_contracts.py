from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def event_payload(amount: str = "10.00") -> dict[str, str]:
    return {
        "portfolio_id": "00000000-0000-0000-0000-000000000001",
        "event_type": "CASH_DEPOSIT",
        "event_date": "2026-08-31",
        "currency": "BRL",
        "cash_amount": amount,
    }


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


def test_idempotency_replay_and_payload_conflict() -> None:
    key = f"contract-{uuid4()}"
    headers = {"Idempotency-Key": key}
    first = client.post("/api/v1/portfolio-events", json=event_payload(), headers=headers)
    replay = client.post("/api/v1/portfolio-events", json=event_payload(), headers=headers)
    conflict = client.post("/api/v1/portfolio-events", json=event_payload("11.00"), headers=headers)

    assert first.status_code == replay.status_code == 202
    assert first.json() == replay.json()
    assert conflict.status_code == 409
    assert conflict.headers["content-type"].startswith("application/problem+json")
    assert "postgresql://" not in conflict.text
