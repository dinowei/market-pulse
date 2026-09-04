from datetime import date, datetime, timezone
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


class RegisterRequest(StrictModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)

    @model_validator(mode="after")
    def validate_credentials(self) -> "RegisterRequest":
        normalized = self.email.strip().casefold()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("invalid email")
        if not any(char.isalpha() for char in self.password) or not any(
            char.isdigit() for char in self.password
        ):
            raise ValueError("password must contain letters and digits")
        self.email = normalized
        return self


class LoginRequest(StrictModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def normalize_email(self) -> "LoginRequest":
        self.email = self.email.strip().casefold()
        return self


class AuthUserResponse(StrictModel):
    id: str
    email: str
    status: str


class AuthSessionResponse(AuthUserResponse):
    expires_at: datetime


class WatchlistCreateRequest(StrictModel):
    name: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def normalize_name(self) -> "WatchlistCreateRequest":
        self.name = " ".join(self.name.split())
        if not self.name:
            raise ValueError("watchlist name is required")
        return self


class WatchlistPatchRequest(StrictModel):
    name: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def normalize_name(self) -> "WatchlistPatchRequest":
        self.name = " ".join(self.name.split())
        if not self.name:
            raise ValueError("watchlist name is required")
        return self


class WatchlistItemCreateRequest(StrictModel):
    canonical_id: str = Field(min_length=3, max_length=160)


class WatchlistReorderRequest(StrictModel):
    canonical_ids: list[str] = Field(min_length=1, max_length=100)


class WatchlistItemResponse(StrictModel):
    id: str
    canonical_id: str
    symbol: str
    display_symbol: str
    name: str
    instrument_type: str
    exchange: str | None = None
    currency: str = Field(pattern="^[A-Z]{3}$")
    timezone: str
    support_state: str
    position: int = Field(ge=0)


class WatchlistResponse(StrictModel):
    id: str
    name: str
    is_system: bool
    items: list[WatchlistItemResponse]
    created_at: datetime
    updated_at: datetime


class WatchlistListResponse(StrictModel):
    items: list[WatchlistResponse]


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


class HistoryPeriod(StrEnum):
    ONE_D = "1D"
    FIVE_D = "5D"
    ONE_M = "1M"
    THREE_M = "3M"
    SIX_M = "6M"
    YTD = "YTD"
    ONE_Y = "1A"
    FIVE_Y = "5A"
    MAX = "MAX"


class PublicQuote(StrictModel):
    canonical_id: str
    symbol: str
    name: str
    asset_type: str
    exchange: str | None = None
    currency: str = Field(pattern="^[A-Z]{3}$")
    price: Decimal | None = None
    change: Decimal | None = None
    change_percent: Decimal | None = None
    data_level: DataLevel
    freshness: Freshness
    provider: str
    dataset: str
    timestamp_official: datetime | None = None
    timestamp_collected: datetime
    latency_ms: int | None = Field(default=None, ge=0)
    limitations: tuple[str, ...] = ()
    unavailable_reason: str | None = None
    request_id: str

    @model_validator(mode="after")
    def require_quote_provenance(self) -> "PublicQuote":
        if self.freshness is not Freshness.UNAVAILABLE and (
            self.price is None or self.timestamp_official is None or self.latency_ms is None
        ):
            raise ValueError("public quote requires complete provenance")
        return self


class PublicHistoryPoint(StrictModel):
    timestamp: datetime
    session_date: date
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    volume: Decimal | None = None
    value: Decimal | None = None
    index_100: Decimal | None = None
    is_gap: bool = False


class PublicHistorySeries(StrictModel):
    canonical_id: str
    symbol: str
    period: HistoryPeriod
    mode: SeriesMode
    adjustment_type: str
    currency: str = Field(pattern="^[A-Z]{3}$")
    data_level: DataLevel
    freshness: Freshness
    provider: str
    dataset: str
    timestamp_official: datetime | None = None
    timestamp_collected: datetime
    latency_ms: int | None = Field(default=None, ge=0)
    limitations: tuple[str, ...] = ()
    points: list[PublicHistoryPoint]
    tabular_fallback: bool = True
    accessibility: dict[str, bool]
    unavailable_reason: str | None = None
    request_id: str

    @model_validator(mode="after")
    def require_series_provenance(self) -> "PublicHistorySeries":
        if self.freshness is not Freshness.UNAVAILABLE and (
            self.timestamp_official is None or self.latency_ms is None
        ):
            raise ValueError("public series requires complete provenance")
        if self.accessibility.get("smoothed", False):
            raise ValueError("series smoothing is not allowed")
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


class PortfolioCreateRequest(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    base_currency: str = Field(pattern="^[A-Z]{3}$")

    @model_validator(mode="after")
    def normalize_name(self) -> "PortfolioCreateRequest":
        self.name = " ".join(self.name.split())
        if not self.name:
            raise ValueError("portfolio name is required")
        return self


class PortfolioPatchRequest(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    base_currency: str | None = Field(default=None, pattern="^[A-Z]{3}$")

    @model_validator(mode="after")
    def validate_patch(self) -> "PortfolioPatchRequest":
        if self.name is None and self.base_currency is None:
            raise ValueError("portfolio patch cannot be empty")
        if self.name is not None:
            self.name = " ".join(self.name.split())
            if not self.name:
                raise ValueError("portfolio name is required")
        return self


class PortfolioResponse(StrictModel):
    id: str
    name: str
    base_currency: str = Field(pattern="^[A-Z]{3}$")
    created_at: datetime
    updated_at: datetime


class PortfolioListResponse(StrictModel):
    items: list[PortfolioResponse]


class PortfolioEventRequest(StrictModel):
    event_type: PortfolioEventType
    currency: str = Field(pattern="^[A-Z]{3}$")
    canonical_id: str | None = Field(default=None, min_length=3, max_length=160)
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    gross_amount: Decimal | None = None
    fee_amount: Decimal | None = None
    notes: str | None = Field(default=None, max_length=2000)
    reversal_of_event_id: str | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def require_utc_timestamp(self) -> "PortfolioEventRequest":
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must include timezone")
        self.occurred_at = self.occurred_at.astimezone(timezone.utc)
        return self


class PortfolioEventResponse(StrictModel):
    id: str
    portfolio_id: str
    event_type: PortfolioEventType
    occurred_at: datetime
    canonical_id: str | None = None
    currency: str = Field(pattern="^[A-Z]{3}$")
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    gross_amount: Decimal | None = None
    fee_amount: Decimal | None = None
    notes: str | None = None
    idempotency_key: str
    reversal_of_event_id: str | None = None
    created_at: datetime
    request_id: str


class PortfolioPositionResponse(StrictModel):
    canonical_id: str
    quantity: Decimal
    total_cost: Decimal
    weighted_average_cost: Decimal


class PortfolioCashBalanceResponse(StrictModel):
    currency: str = Field(pattern="^[A-Z]{3}$")
    balance: Decimal


class PortfolioSummaryResponse(StrictModel):
    portfolio_id: str
    base_currency: str = Field(pattern="^[A-Z]{3}$")
    cash_balances: dict[str, Decimal]
    positions: list[PortfolioPositionResponse]
    event_count: int
    last_event_at: datetime | None = None


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
