from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.market_data.corporate_actions import (
    CorporateActionsReconciler,
    CorporateActionStatus,
    CorporateActionType,
    CorporateActionValidationError,
    normalize_corporate_action,
    project_split_quantity,
)
from app.providers.demo import DemoProvider
from app.providers.licensing import LicenseDecision, LicenseService
from app.providers.models import DataLevel, ProviderDatasetRef

COLLECTED_AT = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)


def dividend_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "action_type": "CASH_DIVIDEND",
        "external_id": "div-001",
        "ex_date": "2026-09-01",
        "payment_date": "2026-09-10",
        "currency": "BRL",
        "gross_amount_per_share": "0.25",
        "source_timestamp": "2026-08-20T12:00:00Z",
    }
    payload.update(overrides)
    return payload


def split_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "action_type": "SPLIT",
        "external_id": "split-001",
        "effective_date": "2026-09-01",
        "split_ratio_from": "1",
        "split_ratio_to": "2",
        "source_timestamp": "2026-08-20T12:00:00Z",
    }
    payload.update(overrides)
    return payload


def normalize(payload: dict[str, object]):
    return normalize_corporate_action(
        payload,
        instrument_id="equity.br.b3.petr4",
        provider="demo",
        dataset="demo-corporate-actions",
        collected_at=COLLECTED_AT,
    )


def test_dividend_is_normalized_with_decimal_and_dates() -> None:
    event = normalize(dividend_payload())
    assert event.action_type is CorporateActionType.CASH_DIVIDEND
    assert event.gross_amount_per_share == Decimal("0.25")
    assert event.ex_date == date(2026, 9, 1)
    assert event.status is CorporateActionStatus.PENDING


def test_jcp_is_normalized_with_decimal() -> None:
    event = normalize(dividend_payload(action_type="JCP", gross_amount_per_share="0.12"))
    assert event.action_type is CorporateActionType.JCP
    assert event.gross_amount_per_share == Decimal("0.12")


def test_split_and_reverse_split_use_positive_decimal_ratios() -> None:
    split = normalize(split_payload())
    reverse = normalize(
        split_payload(action_type="REVERSE_SPLIT", split_ratio_from="10", split_ratio_to="1")
    )
    assert (split.split_ratio_from, split.split_ratio_to) == (Decimal("1"), Decimal("2"))
    assert (reverse.split_ratio_from, reverse.split_ratio_to) == (Decimal("10"), Decimal("1"))


@pytest.mark.parametrize("field", ["currency"])
def test_dividend_missing_required_field_is_blocked(field: str) -> None:
    payload = dividend_payload()
    payload.pop(field)
    with pytest.raises(CorporateActionValidationError):
        normalize(payload)


def test_dividend_without_ex_date_is_unavailable_without_inference() -> None:
    event = normalize(dividend_payload(ex_date=None))
    assert event.status is CorporateActionStatus.UNAVAILABLE
    assert event.ex_date is None


@pytest.mark.parametrize("amount", ["0", "-0.1"])
def test_dividend_non_positive_amount_is_rejected(amount: str) -> None:
    with pytest.raises(CorporateActionValidationError):
        normalize(dividend_payload(gross_amount_per_share=amount))


@pytest.mark.parametrize("ratio", ["0", "-1"])
def test_split_non_positive_ratio_is_rejected(ratio: str) -> None:
    with pytest.raises(CorporateActionValidationError):
        normalize(split_payload(split_ratio_to=ratio))


def test_same_external_event_is_idempotent() -> None:
    reconciler = CorporateActionsReconciler()
    event = normalize(dividend_payload())
    assert reconciler.ingest(event) == "inserted"
    assert reconciler.ingest(event) == "unchanged"
    assert len(reconciler.active_events()) == 1


def test_correction_preserves_previous_version() -> None:
    reconciler = CorporateActionsReconciler()
    original = normalize(dividend_payload())
    corrected = normalize(
        dividend_payload(gross_amount_per_share="0.30", correction_reason="provider correction")
    )
    reconciler.ingest(original)
    assert reconciler.ingest(corrected) == "corrected"
    history = reconciler.history(original.external_event_key)
    assert len(history) == 2
    assert history[0].status is CorporateActionStatus.CORRECTED
    assert history[1].version == 2


def test_cancellation_preserves_original_event() -> None:
    reconciler = CorporateActionsReconciler()
    original = normalize(dividend_payload())
    cancelled = normalize(
        dividend_payload(status="CANCELLED", cancellation_reason="cancelled by issuer")
    )
    reconciler.ingest(original)
    assert reconciler.ingest(cancelled) == "cancelled"
    history = reconciler.history(original.external_event_key)
    assert len(history) == 2
    assert history[0].status is CorporateActionStatus.PENDING
    assert history[1].status is CorporateActionStatus.CANCELLED


def test_conflicting_event_goes_to_quarantine() -> None:
    reconciler = CorporateActionsReconciler()
    reconciler.ingest(normalize(dividend_payload()))
    conflict = normalize(dividend_payload(gross_amount_per_share="0.30"))
    assert reconciler.ingest(conflict) == "quarantined"
    assert reconciler.quarantine[-1].reason == "CONFLICTING_EVENT"


def test_batch_isolates_invalid_event_from_valid_event() -> None:
    result = CorporateActionsReconciler().ingest_batch(
        [normalize(dividend_payload()), "not-an-event"]
    )
    assert result == ["inserted", "quarantined"]


def test_split_projection_preserves_economic_value_without_portfolio_write() -> None:
    quantity, value = project_split_quantity(
        quantity=Decimal("10"),
        unit_price=Decimal("100"),
        ratio_from=Decimal("1"),
        ratio_to=Decimal("2"),
    )
    assert quantity == Decimal("20")
    assert value == Decimal("1000")


def test_float_values_are_rejected() -> None:
    with pytest.raises(CorporateActionValidationError):
        normalize(dividend_payload(gross_amount_per_share=0.25))


def test_raw_payload_is_sanitized() -> None:
    event = normalize(dividend_payload(token="do-not-retain"))
    assert event.raw_payload["token"] == "[REDACTED]"


def test_unreviewed_provider_remains_blocked() -> None:
    decision = LicenseService().decide(
        ProviderDatasetRef(
            provider="candidate",
            dataset="candidate-events",
            license_status="UNREVIEWED",
        )
    )
    assert decision is LicenseDecision.BLOCK


def test_demo_provider_events_are_marked_demo() -> None:
    result = DemoProvider().corporate_actions("equity.br.b3.petr4")
    assert result.provenance.data_level is DataLevel.DEMO
    assert result.value[0]["action_type"] == "SPLIT"
    assert result.value[0]["split_ratio_from"] == Decimal("1")
    assert result.value[0]["split_ratio_to"] == Decimal("2")
