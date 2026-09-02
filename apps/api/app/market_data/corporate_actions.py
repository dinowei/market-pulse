"""Deterministic normalization and reconciliation for corporate actions.

This module deliberately stops at event ingestion.  Applying an event to a
user portfolio remains the responsibility of the later portfolio domain.
"""

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any
from uuid import uuid4

from app.providers.raw_payload import sanitize_payload


class CorporateActionType(StrEnum):
    CASH_DIVIDEND = "CASH_DIVIDEND"
    JCP = "JCP"
    SPLIT = "SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"


class CorporateActionStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CORRECTED = "CORRECTED"
    CANCELLED = "CANCELLED"
    UNAVAILABLE = "UNAVAILABLE"


class CorporateActionValidationError(ValueError):
    """Raised when a corporate-action payload cannot be safely normalized."""


@dataclass(frozen=True)
class CorporateAction:
    event_id: str
    instrument_id: str
    provider: str
    dataset: str
    external_event_key: str
    action_type: CorporateActionType
    status: CorporateActionStatus
    announced_date: date | None
    ex_date: date | None
    record_date: date | None
    payment_date: date | None
    effective_date: date | None
    currency: str | None
    gross_amount_per_share: Decimal | None
    net_amount_per_share: Decimal | None
    withholding_tax_rate: Decimal | None
    split_ratio_from: Decimal | None
    split_ratio_to: Decimal | None
    external_id: str | None
    source_timestamp: datetime | None
    collected_at: datetime
    created_at: datetime
    updated_at: datetime
    ingestion_batch_id: str | None = None
    raw_payload_record_id: str | None = None
    raw_payload: Any = None
    version: int = 1
    supersedes_event_id: str | None = None
    corrected_event_id: str | None = None
    cancellation_reason: str | None = None
    correction_reason: str | None = None


@dataclass(frozen=True)
class QuarantinedCorporateAction:
    reason: str
    event: CorporateAction | None
    payload: Any = None


def _decimal(value: Any, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, float):
        raise CorporateActionValidationError(f"{field_name} cannot be float")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise CorporateActionValidationError(f"Invalid {field_name}") from exc
    if not result.is_finite():
        raise CorporateActionValidationError(f"Invalid {field_name}")
    return result


def _date(value: Any, field_name: str) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise CorporateActionValidationError(f"Invalid {field_name}") from exc
    raise CorporateActionValidationError(f"Invalid {field_name}")


def _timestamp(value: Any, field_name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, (str, datetime)):
        raise CorporateActionValidationError(f"Invalid {field_name}")
    try:
        parsed = (
            value
            if isinstance(value, datetime)
            else datetime.fromisoformat(value.replace("Z", "+00:00"))
        )
    except ValueError as exc:
        raise CorporateActionValidationError(f"Invalid {field_name}") from exc
    if parsed.tzinfo is None:
        raise CorporateActionValidationError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _positive(value: Decimal | None, field_name: str) -> Decimal | None:
    if value is not None and value <= 0:
        raise CorporateActionValidationError(f"{field_name} must be positive")
    return value


def _event_key(
    *,
    provider: str,
    dataset: str,
    instrument_id: str,
    action_type: CorporateActionType,
    external_id: str | None,
    ex_date: date | None,
    effective_date: date | None,
    payment_date: date | None,
) -> str:
    identity = {
        "action_type": action_type.value,
        "dataset": dataset,
        "effective_date": effective_date.isoformat() if effective_date else None,
        "ex_date": ex_date.isoformat() if ex_date else None,
        "external_id": external_id,
        "instrument_id": instrument_id,
        "payment_date": payment_date.isoformat() if payment_date else None,
        "provider": provider,
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _fingerprint(event: CorporateAction) -> str:
    values = {
        "action_type": event.action_type.value,
        "currency": event.currency,
        "effective_date": event.effective_date.isoformat() if event.effective_date else None,
        "ex_date": event.ex_date.isoformat() if event.ex_date else None,
        "gross_amount_per_share": str(event.gross_amount_per_share),
        "net_amount_per_share": str(event.net_amount_per_share),
        "payment_date": event.payment_date.isoformat() if event.payment_date else None,
        "record_date": event.record_date.isoformat() if event.record_date else None,
        "split_ratio_from": str(event.split_ratio_from),
        "split_ratio_to": str(event.split_ratio_to),
        "withholding_tax_rate": str(event.withholding_tax_rate),
    }
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def normalize_corporate_action(
    payload: dict[str, Any],
    *,
    instrument_id: str,
    provider: str,
    dataset: str,
    collected_at: datetime,
) -> CorporateAction:
    if not instrument_id or not provider or not dataset:
        raise CorporateActionValidationError("instrument, provider and dataset are required")
    try:
        action_type = CorporateActionType(payload["action_type"])
    except (KeyError, ValueError) as exc:
        raise CorporateActionValidationError("Unsupported action_type") from exc
    try:
        status = CorporateActionStatus(payload.get("status", CorporateActionStatus.PENDING))
    except ValueError as exc:
        raise CorporateActionValidationError("Unsupported status") from exc
    normalized_collected_at = _timestamp(collected_at, "collected_at")
    if normalized_collected_at is None:
        raise CorporateActionValidationError("collected_at is required")
    source_timestamp = _timestamp(payload.get("source_timestamp"), "source_timestamp")
    announced_date = _date(payload.get("announced_date"), "announced_date")
    ex_date = _date(payload.get("ex_date"), "ex_date")
    record_date = _date(payload.get("record_date"), "record_date")
    payment_date = _date(payload.get("payment_date"), "payment_date")
    effective_date = _date(payload.get("effective_date"), "effective_date")
    currency = payload.get("currency")
    if action_type in (CorporateActionType.CASH_DIVIDEND, CorporateActionType.JCP):
        if not isinstance(currency, str) or len(currency) != 3 or currency != currency.upper():
            raise CorporateActionValidationError("ISO currency is required")
        amount = _positive(
            _decimal(
                payload.get("gross_amount_per_share", payload.get("amount")),
                "gross_amount_per_share",
            ),
            "gross_amount_per_share",
        )
        if amount is None:
            raise CorporateActionValidationError("gross_amount_per_share is required")
        if ex_date is None and status is not CorporateActionStatus.CANCELLED:
            status = CorporateActionStatus.UNAVAILABLE
    else:
        amount = None
        currency = currency if isinstance(currency, str) else None
    ratio_from = _positive(
        _decimal(payload.get("split_ratio_from"), "split_ratio_from"), "split_ratio_from"
    )
    ratio_to = _positive(
        _decimal(payload.get("split_ratio_to"), "split_ratio_to"), "split_ratio_to"
    )
    if action_type in (CorporateActionType.SPLIT, CorporateActionType.REVERSE_SPLIT):
        if ratio_from is None or ratio_to is None or effective_date is None:
            raise CorporateActionValidationError("split ratios and effective_date are required")
    else:
        ratio_from = ratio_to = None
    external_id = payload.get("external_id")
    if external_id is not None and not isinstance(external_id, str):
        raise CorporateActionValidationError("external_id must be text")
    return CorporateAction(
        event_id=str(uuid4()),
        instrument_id=instrument_id,
        provider=provider,
        dataset=dataset,
        external_event_key=_event_key(
            provider=provider,
            dataset=dataset,
            instrument_id=instrument_id,
            action_type=action_type,
            external_id=external_id,
            ex_date=ex_date,
            effective_date=effective_date,
            payment_date=payment_date,
        ),
        action_type=action_type,
        status=status,
        announced_date=announced_date,
        ex_date=ex_date,
        record_date=record_date,
        payment_date=payment_date,
        effective_date=effective_date,
        currency=currency,
        gross_amount_per_share=amount,
        net_amount_per_share=_decimal(payload.get("net_amount_per_share"), "net_amount_per_share"),
        withholding_tax_rate=_decimal(payload.get("withholding_tax_rate"), "withholding_tax_rate"),
        split_ratio_from=ratio_from,
        split_ratio_to=ratio_to,
        external_id=external_id,
        source_timestamp=source_timestamp,
        collected_at=normalized_collected_at,
        created_at=normalized_collected_at,
        updated_at=normalized_collected_at,
        ingestion_batch_id=payload.get("ingestion_batch_id"),
        raw_payload_record_id=payload.get("raw_payload_record_id"),
        raw_payload=sanitize_payload(payload),
        cancellation_reason=payload.get("cancellation_reason"),
        correction_reason=payload.get("correction_reason"),
    )


@dataclass
class CorporateActionsReconciler:
    _events: dict[str, list[CorporateAction]] = field(default_factory=dict)
    quarantine: list[QuarantinedCorporateAction] = field(default_factory=list)

    def ingest(self, event: CorporateAction) -> str:
        history = self._events.setdefault(event.external_event_key, [])
        if not history:
            history.append(event)
            return "inserted"
        current = history[-1]
        if _fingerprint(current) == _fingerprint(event) and event.status == current.status:
            return "unchanged"
        if event.status is CorporateActionStatus.CANCELLED:
            history.append(
                replace(event, version=current.version + 1, supersedes_event_id=current.event_id)
            )
            return "cancelled"
        if event.correction_reason:
            history[-1] = replace(
                current,
                status=CorporateActionStatus.CORRECTED,
                correction_reason=event.correction_reason,
            )
            history.append(
                replace(
                    event,
                    version=current.version + 1,
                    supersedes_event_id=current.event_id,
                    corrected_event_id=current.event_id,
                )
            )
            return "corrected"
        self.quarantine.append(QuarantinedCorporateAction("CONFLICTING_EVENT", event))
        return "quarantined"

    def ingest_batch(self, events: list[CorporateAction | Any]) -> list[str]:
        outcomes: list[str] = []
        for event in events:
            if not isinstance(event, CorporateAction):
                self.quarantine.append(QuarantinedCorporateAction("INVALID_EVENT", None, event))
                outcomes.append("quarantined")
                continue
            outcomes.append(self.ingest(event))
        return outcomes

    def history(self, external_event_key: str) -> tuple[CorporateAction, ...]:
        return tuple(self._events.get(external_event_key, ()))

    def active_events(self) -> tuple[CorporateAction, ...]:
        return tuple(history[-1] for history in self._events.values())


def project_split_quantity(
    *, quantity: Decimal, unit_price: Decimal, ratio_from: Decimal, ratio_to: Decimal
) -> tuple[Decimal, Decimal]:
    for name, value in (
        ("quantity", quantity),
        ("unit_price", unit_price),
        ("ratio_from", ratio_from),
        ("ratio_to", ratio_to),
    ):
        if isinstance(value, float) or not isinstance(value, Decimal):
            raise CorporateActionValidationError(f"{name} must be Decimal")
        if value <= 0:
            raise CorporateActionValidationError(f"{name} must be positive")
    return quantity * ratio_to / ratio_from, quantity * unit_price
