from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DataLevel(StrEnum):
    REAL_TIME = "REAL_TIME"
    DELAYED = "DELAYED"
    EOD = "EOD"
    DEMO = "DEMO"


class Freshness(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class ProviderCapability(StrEnum):
    LATEST_QUOTE = "latest_quote"
    HISTORICAL_BARS = "historical_bars"
    FX_RATES = "fx_rates"
    INSTRUMENT_METADATA = "instrument_metadata"
    DIVIDENDS = "dividends"
    CORPORATE_ACTIONS = "corporate_actions"


class ProviderLatencyMode(StrEnum):
    REAL_TIME = "REAL_TIME"
    DELAYED = "DELAYED"
    BATCH = "BATCH"


class ProviderDatasetRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    license_status: str = Field(min_length=1)
    public_approved: bool = False
    evidence: bool = False
    # Licensing dimensions are explicit so a dataset cannot be reused in an
    # unreviewed plan, endpoint, purpose, modality, or environment.
    plan: str | None = None
    endpoint: str | None = None
    purpose: str | None = None
    modality: str | None = None
    environment: str | None = None


class ProviderProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_timestamp: datetime
    collected_at: datetime
    data_level: DataLevel
    freshness: Freshness
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    exchange: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    limitations: tuple[str, ...] = ()


T = TypeVar("T")


class ProviderResult(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")

    value: T
    provenance: ProviderProvenance

    @field_validator("value", mode="before")
    @classmethod
    def reject_financial_floats(cls, value: T) -> T:
        def contains_float(item: object) -> bool:
            if isinstance(item, float):
                return True
            if isinstance(item, dict):
                return any(contains_float(key) or contains_float(val) for key, val in item.items())
            if isinstance(item, (list, tuple, set)):
                return any(contains_float(child) for child in item)
            return False

        if contains_float(value):
            raise ValueError("provider financial values cannot be float")
        return value

    @model_validator(mode="after")
    def ensure_provenance(self) -> "ProviderResult[T]":
        if self.provenance is None:
            raise ValueError("Provider results require provenance")
        return self


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def decimal_value(value: Decimal | int | str) -> Decimal:
    if isinstance(value, float):
        raise TypeError("Financial values cannot be float")
    return Decimal(value)
