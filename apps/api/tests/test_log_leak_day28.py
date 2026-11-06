"""Credentials carried by a request must never surface in logs or responses.

The application code does not call the logging module today, so the caplog side of
this test is a regression guard for the moment it starts to. The response-body side
covers the surface that is actually reachable now.
"""

import logging

from fastapi.testclient import TestClient

from app.main import app

# Deliberately fake. The connection string uses the local_only placeholder password
# that scripts/week1_gate.py treats as an explicit non-secret.
FAKE_BEARER = "Bearer fake-authorization-value-not-real"
FAKE_COOKIE = "fake-session-value-not-real"
FAKE_DSN = "postgresql://fake_user:local_only@fake.invalid:5432/fake_db"
FAKE_VALUES = (FAKE_BEARER, "fake-authorization-value-not-real", FAKE_COOKIE, FAKE_DSN)


def _assert_nothing_leaked(caplog, *bodies: str) -> None:
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for value in FAKE_VALUES:
        assert value not in logged, f"credential leaked into logs: {value}"
        for body in bodies:
            assert value not in body, f"credential leaked into response: {value}"


def test_credentials_never_reach_logs_or_error_responses(caplog) -> None:
    client = TestClient(app)
    headers = {
        "Authorization": FAKE_BEARER,
        "X-Connection-String": FAKE_DSN,
    }

    with caplog.at_level(logging.DEBUG):
        not_found = client.get("/api/v1/not-found", headers=headers)
        invalid = client.get("/api/v1/instruments?limit=101", headers=headers)
        csrf = client.post(
            "/api/v1/auth/logout",
            headers={**headers, "Origin": "https://untrusted.invalid"},
            cookies={"market_pulse_session": FAKE_COOKIE},
        )
        body_echo = client.post(
            "/api/v1/auth/login",
            headers={**headers, "Origin": "http://localhost:3000"},
            json={"email": "person@example.invalid", "password": FAKE_DSN},
        )

    assert not_found.status_code == 404
    assert invalid.status_code == 422
    assert csrf.status_code == 403
    assert body_echo.status_code in {401, 422, 503}

    _assert_nothing_leaked(caplog, not_found.text, invalid.text, csrf.text, body_echo.text)


def test_error_responses_never_expose_the_configured_database_url(caplog) -> None:
    from app.core.config import get_settings

    client = TestClient(app)
    with caplog.at_level(logging.DEBUG):
        response = client.get("/api/v1/not-found")

    assert response.status_code == 404
    assert "postgresql://" not in response.text
    assert "Traceback" not in response.text
    assert get_settings().database_url not in response.text
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "postgresql://" not in logged
