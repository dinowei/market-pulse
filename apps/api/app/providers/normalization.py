from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.providers.models import ProviderProvenance, ProviderResult


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, float) or value is None:
        raise ValueError(f"Invalid {field}")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid {field}") from exc


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Invalid timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must be timezone-aware")
    return parsed


def _provenance(
    provider: str, dataset: str, currency: str, timestamp: datetime
) -> ProviderProvenance:
    if not isinstance(currency, str) or len(currency) != 3 or currency.upper() != currency:
        raise ValueError("Invalid currency")
    now = timestamp
    return ProviderProvenance(
        provider=provider,
        dataset=dataset,
        source=provider,
        source_timestamp=timestamp,
        collected_at=now,
        data_level="DELAYED",
        freshness="FRESH",
        currency=currency,
    )


class NormalizedQuote(ProviderResult[Decimal]):
    canonical_id: str
    price: Decimal

    @property
    def source_timestamp(self) -> datetime:
        return self.provenance.source_timestamp


def normalize_quote(
    payload: dict[str, Any], canonical_id: str, provider: str, dataset: str
) -> NormalizedQuote:
    currency = payload.get("currency")
    if not isinstance(currency, str) or len(currency) != 3 or currency.upper() != currency:
        raise ValueError("Invalid currency")
    timestamp = _timestamp(payload.get("timestamp"))
    price = _decimal(payload.get("price"), "price")
    return NormalizedQuote(
        value=price,
        price=price,
        canonical_id=canonical_id,
        provenance=_provenance(provider, dataset, currency, timestamp),
    )


class NormalizedOHLCV(ProviderResult[dict[str, Decimal]]):
    canonical_id: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None

    @property
    def source_timestamp(self) -> datetime:
        return self.provenance.source_timestamp


def normalize_ohlcv(
    payload: dict[str, Any], canonical_id: str, provider: str, dataset: str
) -> NormalizedOHLCV:
    timestamp = _timestamp(payload.get("t"))
    values = {
        key: _decimal(payload.get(short), key)
        for key, short in (("open", "o"), ("high", "h"), ("low", "l"), ("close", "c"))
    }
    currency = payload.get("currency")
    if not isinstance(currency, str) or len(currency) != 3 or currency.upper() != currency:
        raise ValueError("Invalid currency")
    if values["high"] < max(values["open"], values["close"]) or values["low"] > min(
        values["open"], values["close"]
    ) or values["high"] < values["low"]:
        raise ValueError("Invalid OHLC invariants")
    volume = None if payload.get("v") is None else _decimal(payload.get("v"), "volume")
    values_dict = {**values, **({"volume": volume} if volume is not None else {})}
    return NormalizedOHLCV(
        value=values_dict,
        canonical_id=canonical_id,
        **values,
        volume=volume,
        provenance=_provenance(provider, dataset, currency, timestamp),
    )
