from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any


class AdjustmentType(StrEnum):
    UNADJUSTED = "UNADJUSTED"
    ADJUSTED_SPLIT_ONLY = "ADJUSTED_SPLIT_ONLY"
    ADJUSTED_TOTAL_RETURN = "ADJUSTED_TOTAL_RETURN"


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, float) or value is None:
        raise ValueError(f"Invalid {field}")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid {field}") from exc
    if not number.is_finite():
        raise ValueError(f"Invalid {field}")
    return number


def _utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Timestamp is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class MarketBar:
    canonical_id: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    currency: str
    adjustment_type: AdjustmentType

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MarketBar":
        canonical_id = payload.get("canonical_id")
        currency = payload.get("currency")
        if not isinstance(canonical_id, str) or not canonical_id:
            raise ValueError("canonical_id is required")
        if not isinstance(currency, str) or len(currency) != 3 or currency != currency.upper():
            raise ValueError("ISO currency is required")
        try:
            adjustment = AdjustmentType(payload["adjustment_type"])
        except (KeyError, ValueError) as exc:
            raise ValueError("adjustment_type is required") from exc
        values = {
            field: _decimal(payload.get(field), field) for field in ("open", "high", "low", "close")
        }
        volume = _decimal(payload.get("volume", "0"), "volume")
        if min(values.values()) <= 0 or values["low"] > values["high"]:
            raise ValueError("INVALID_OHLC")
        if not values["low"] <= values["open"] <= values["high"]:
            raise ValueError("INVALID_OHLC")
        if not values["low"] <= values["close"] <= values["high"]:
            raise ValueError("INVALID_OHLC")
        return cls(
            canonical_id=canonical_id,
            timestamp=_utc(payload.get("timestamp")),
            volume=volume,
            currency=currency,
            adjustment_type=adjustment,
            **values,
        )


@dataclass(frozen=True)
class FxRate:
    base_currency: str
    quote_currency: str
    rate: Decimal
    timestamp: datetime

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "FxRate":
        base, quote = payload.get("base_currency"), payload.get("quote_currency")
        if (
            not all(
                isinstance(value, str) and len(value) == 3 and value == value.upper()
                for value in (base, quote)
            )
            or base == quote
        ):
            raise ValueError("Distinct ISO currencies are required")
        rate = _decimal(payload.get("rate"), "rate")
        if rate <= 0:
            raise ValueError("FX rate must be positive")
        return cls(
            base_currency=base,
            quote_currency=quote,
            rate=rate,
            timestamp=_utc(payload.get("timestamp")),
        )


@dataclass(frozen=True)
class QuarantinedRecord:
    reason: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class OutlierPolicy:
    max_change_ratio: Decimal = Decimal("0.5")


@dataclass(frozen=True)
class BatchResult:
    accepted: tuple[MarketBar, ...]
    quarantined: tuple[QuarantinedRecord, ...]


def normalize_batch(payloads: list[dict[str, Any]], policy: OutlierPolicy) -> BatchResult:
    accepted: list[MarketBar] = []
    quarantined: list[QuarantinedRecord] = []
    for payload in payloads:
        try:
            item = MarketBar.from_payload(payload)
            if (
                accepted
                and abs(item.close - accepted[-1].close) / accepted[-1].close
                > policy.max_change_ratio
            ):
                raise ValueError("OUTLIER_EXTREME")
            accepted.append(item)
        except ValueError as exc:
            reason = (
                str(exc) if str(exc) in {"INVALID_OHLC", "OUTLIER_EXTREME"} else "INVALID_PAYLOAD"
            )
            quarantined.append(QuarantinedRecord(reason, payload))
    return BatchResult(tuple(accepted), tuple(quarantined))
