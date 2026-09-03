from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DataLevel(StrEnum):
    REAL_TIME = "REAL_TIME"
    DELAYED = "DELAYED"
    EOD = "EOD"
    DEMO = "DEMO"


class Freshness(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class ContentType(StrEnum):
    FACT = "FACT"
    THIRD_PARTY_CONSENSUS = "THIRD_PARTY_CONSENSUS"
    CONDITIONAL_SCENARIO = "CONDITIONAL_SCENARIO"
    RISK = "RISK"
    LIMITATION = "LIMITATION"


class PublicationStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    VALIDATED = "VALIDATED"
    IN_REVIEW = "IN_REVIEW"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"


class PortfolioEventType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    CASH_DEPOSIT = "CASH_DEPOSIT"
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL"
    FEE = "FEE"
    DIVIDEND = "DIVIDEND"
    SPLIT = "SPLIT"
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Pagination(StrictModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort: str = "created_at"
    order: str = Field(default="desc", pattern="^(asc|desc)$")


class PageMeta(StrictModel):
    limit: int
    offset: int
    next_offset: int | None


class InstrumentSummary(StrictModel):
    id: str
    canonical_id: str
    symbol: str
    display_symbol: str
    name: str
    instrument_type: str
    currency: str = Field(pattern="^[A-Z]{3}$")
    aliases: tuple[str, ...] = ()
    catalog_status: str
    coverage_tier: str
    data_support_status: str
    support_state: str


class InstrumentList(StrictModel):
    items: list[InstrumentSummary]
    meta: PageMeta


class QuoteContract(StrictModel):
    instrument_id: str
    price: Decimal
    currency: str = Field(pattern="^[A-Z]{3}$")
    data_level: DataLevel
    freshness: Freshness
    source: str
    dataset: str
    source_timestamp: datetime | None = None
    collected_at: datetime | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    limitations: tuple[str, ...] = ()
    unavailable_reason: str | None = None

    @model_validator(mode="after")
    def require_provenance(self) -> "QuoteContract":
        if self.freshness is not Freshness.UNAVAILABLE and (
            self.source_timestamp is None or self.collected_at is None or self.latency_ms is None
        ):
            raise ValueError("quote provenance requires timestamps and latency_ms")
        return self


class SeriesMode(StrEnum):
    PRICE = "PRICE"
    INDEX_100 = "INDEX_100"


class HistoricalPoint(StrictModel):
    timestamp: datetime
    value: Decimal


class HistoricalSeries(StrictModel):
    instrument_id: str
    currency: str = Field(pattern="^[A-Z]{3}$")
    source: str
    dataset: str
    data_level: DataLevel
    freshness: Freshness
    source_timestamp: datetime | None = None
    collected_at: datetime | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    limitations: tuple[str, ...] = ()
    unavailable_reason: str | None = None
    mode: SeriesMode = SeriesMode.PRICE
    fallback_tabular: bool = True
    reduced_motion: bool = False
    smoothed: bool = False
    points: list[HistoricalPoint]

    @model_validator(mode="after")
    def require_provenance(self) -> "HistoricalSeries":
        if self.freshness is not Freshness.UNAVAILABLE and (
            self.source_timestamp is None or self.collected_at is None or self.latency_ms is None
        ):
            raise ValueError("series provenance requires timestamps and latency_ms")
        if self.smoothed:
            raise ValueError("financial series cannot use artificial smoothing")
        return self


class PortfolioEventCreate(StrictModel):
    portfolio_id: str
    event_type: PortfolioEventType
    event_date: date
    currency: str = Field(pattern="^[A-Z]{3}$")
    quantity: Decimal | None = None
    price: Decimal | None = None
    gross_amount: Decimal | None = None
    fees: Decimal | None = None
    cash_amount: Decimal | None = None
    note: str | None = Field(default=None, max_length=2000)


class PortfolioEventAccepted(StrictModel):
    status: str = "accepted"
    idempotency_key: str


class ErrorProblem(StrictModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    request_id: str
