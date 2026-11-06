from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import routers
from app.main import app
from app.portfolios.income import (
    IncomeStatus,
    derive_income_status,
    validate_marker_references,
)
from app.telemetry import TelemetryPIIError, validate_web_vitals_payload

client = TestClient(app)


def test_income_status_is_applied_only_after_payment_or_ledger_receipt() -> None:
    assert (
        derive_income_status(
            payment_date=date(2026, 9, 1),
            today=date(2026, 9, 10),
            has_ledger_receipt=False,
            corporate_status="CONFIRMED",
        )
        is IncomeStatus.APPLIED
    )
    assert (
        derive_income_status(
            payment_date=date(2026, 9, 30),
            today=date(2026, 9, 10),
            has_ledger_receipt=False,
            corporate_status="CONFIRMED",
        )
        is IncomeStatus.PENDING
    )
    assert (
        derive_income_status(
            payment_date=None,
            today=date(2026, 9, 10),
            has_ledger_receipt=True,
            corporate_status="UNAVAILABLE",
        )
        is IncomeStatus.APPLIED
    )


def test_marker_referential_integrity_rejects_orphan_ids() -> None:
    markers = [
        {"source_type": "LEDGER_EVENT", "source_id": "ledger-1"},
        {"source_type": "CORPORATE_ACTION", "source_id": "action-1"},
    ]
    validate_marker_references(markers, {"ledger-1"}, {"action-1"})
    with pytest.raises(ValueError, match="orphan marker"):
        validate_marker_references(
            [*markers, {"source_type": "LEDGER_EVENT", "source_id": "missing"}],
            {"ledger-1"},
            {"action-1"},
        )


def test_telemetry_payload_is_aggregated_and_contains_no_pii() -> None:
    aggregate = validate_web_vitals_payload(
        {
            "metric": "LCP",
            "value": "1234.50",
            "route": "/portfolios",
            "sample_count": 3,
        }
    )
    assert aggregate.metric == "LCP"
    assert aggregate.value == Decimal("1234.50")
    assert aggregate.sample_count == 3
    assert aggregate.route == "/portfolios"

    with pytest.raises(TelemetryPIIError):
        validate_web_vitals_payload(
            {
                "metric": "CLS",
                "value": "0.1",
                "email": "person@example.invalid",
            }
        )


def test_telemetry_timestamp_is_timezone_aware_and_metric_is_bounded() -> None:
    aggregate = validate_web_vitals_payload(
        {
            "metric": "INP",
            "value": "200",
            "route": "/",
            "sample_count": 1,
            "observed_at": "2026-09-10T12:00:00Z",
        }
    )
    assert aggregate.observed_at == datetime(2026, 9, 10, 12, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="metric"):
        validate_web_vitals_payload({"metric": "FCP", "value": "1", "route": "/"})


def test_telemetry_endpoint_accepts_only_aggregated_contract() -> None:
    recorded = []

    class FakeService:
        def record(self, aggregate) -> None:
            recorded.append(aggregate)

    app.dependency_overrides[routers.get_web_vitals_service] = lambda: FakeService()
    try:
        response = client.post(
            "/api/v1/telemetry/web-vitals",
            json={"metric": "CLS", "value": "0.04", "route": "/portfolios", "sample_count": 2},
        )
        assert response.status_code == 202
        assert len(recorded) == 1
        assert recorded[0].sample_count == 2
        pii = client.post(
            "/api/v1/telemetry/web-vitals",
            json={"metric": "LCP", "value": "12", "route": "/", "email": "x@example.invalid"},
        )
        assert pii.status_code == 422
    finally:
        app.dependency_overrides.pop(routers.get_web_vitals_service, None)
