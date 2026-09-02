from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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
    symbol: str
    name: str
    instrument_type: str
    currency: str = Field(pattern="^[A-Z]{3}$")


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
    source_timestamp: datetime
    collected_at: datetime


class HistoricalPoint(StrictModel):
    timestamp: datetime
    value: Decimal


class HistoricalSeries(StrictModel):
    instrument_id: str
    currency: str = Field(pattern="^[A-Z]{3}$")
    source: str
    data_level: DataLevel
    freshness: Freshness
    points: list[HistoricalPoint]


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
