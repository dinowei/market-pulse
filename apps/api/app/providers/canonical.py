"""Canonical provider-layer models (ADR-025).

Every vendor normalizer returns these types, so no endpoint re-implements parsing. Bars reuse
`app.market_data.normalization.MarketBar`; quotes and FX rates are defined here. Values are
Decimal and never rounded; timestamps are timezone-aware UTC.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.market_data.normalization import AdjustmentType
from app.providers.models import DataLevel, ProviderError

UTC = timezone.utc
# Clock skew tolerated before a source timestamp counts as "in the future".
FUTURE_TOLERANCE = timedelta(minutes=5)


class UnavailableReason(StrEnum):
    """Codes the API may return instead of a value; the frontend explains each one."""

    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"
    LICENSE_BLOCKED = "LICENSE_BLOCKED"
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"
    DATASET_NOT_APPROVED = "DATASET_NOT_APPROVED"
    SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"
    RATE_LIMITED = "RATE_LIMITED"
    SOURCE_ERROR = "SOURCE_ERROR"


class QualityStatus(StrEnum):
    VALID = "VALID"
    QUARANTINED = "QUARANTINED"


class ValueUnit(StrEnum):
    """What a number measures. Never inferred from `currency` (H-30)."""

    PRICE = "PRICE"
    FX_RATE = "FX_RATE"
    INDEX_POINTS = "INDEX_POINTS"
    UNDECLARED = "UNDECLARED"


class NormalizationError(ProviderError):
    """A payload that cannot become a canonical value; `code` is an UnavailableReason."""

    def __init__(self, reason: UnavailableReason, message: str, *, retryable: bool = False):
        super().__init__(reason.value, message, retryable=retryable)
        self.reason = reason


class CanonicalQuote(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    price: Decimal
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    unit: ValueUnit = ValueUnit.PRICE
    previous_close: Decimal | None = None
    change: Decimal | None = None
    change_percent: Decimal | None = None
    volume: Decimal | None = None
    # A source that only names the session (EOD) leaves source_timestamp empty: the time is
    # unknown and is not invented as midnight.
    source_timestamp: datetime | None = None
    session_date: date | None = None
    ingested_at: datetime
    data_level: DataLevel
    is_demo: bool = False
    adjustment_type: AdjustmentType = AdjustmentType.UNADJUSTED
    quality_status: QualityStatus = QualityStatus.VALID
    quality_notes: tuple[str, ...] = ()
    license_status: str = "UNREVIEWED"
    request_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> "CanonicalQuote":
        if self.price <= 0:
            raise ValueError("price must be positive")
        if self.volume is not None and self.volume < 0:
            raise ValueError("volume cannot be negative")
        if self.source_timestamp is None and self.session_date is None:
            raise ValueError("a source timestamp or session date is required")
        for instant in (self.source_timestamp, self.ingested_at):
            if instant is not None and instant.tzinfo is None:
                raise ValueError("timestamps must be timezone-aware")
        if self.source_timestamp and self.source_timestamp > self.ingested_at + FUTURE_TOLERANCE:
            raise ValueError("source timestamp is in the future")
        if self.is_demo != (self.data_level is DataLevel.DEMO):
            raise ValueError("is_demo must match data_level DEMO")
        return self


class CanonicalFxRate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    base_currency: str = Field(pattern=r"^[A-Z]{3}$")
    quote_currency: str = Field(pattern=r"^[A-Z]{3}$")
    rate: Decimal
    provider: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    source_timestamp: datetime
    ingested_at: datetime
    data_level: DataLevel
    license_status: str = "UNREVIEWED"
    request_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> "CanonicalFxRate":
        if self.base_currency == self.quote_currency:
            raise ValueError("FX currencies must differ")
        if self.rate <= 0:
            raise ValueError("FX rate must be positive")
        if self.source_timestamp.tzinfo is None or self.ingested_at.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        if self.source_timestamp > self.ingested_at + FUTURE_TOLERANCE:
            raise ValueError("source timestamp is in the future")
        return self
