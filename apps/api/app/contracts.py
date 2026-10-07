from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.editorial.validator import EditorialBlock, EditorialStatus


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


class EditorialPostResponse(StrictModel):
    id: str
    slug: str
    title: str
    summary: str | None = None
    content_date: date | None = None
    blocks: tuple[EditorialBlock, ...]
    status: EditorialStatus
    version: int = Field(ge=1)
    created_at: datetime
    published_at: datetime


class EditorialPostListResponse(StrictModel):
    items: list[EditorialPostResponse]


class EditorialAdminPostResponse(EditorialPostResponse):
    published_at: datetime | None = None


class EditorialAdminPostListResponse(StrictModel):
    items: list[EditorialAdminPostResponse]


class EditorialPostCreateRequest(StrictModel):
    slug: str = Field(min_length=3, max_length=180, pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=1, max_length=240)
    summary: str | None = Field(default=None, max_length=2000)
    content_date: date | None = None
    blocks: tuple[EditorialBlock, ...] = ()


class EditorialVersionCreateRequest(StrictModel):
    title: str = Field(min_length=1, max_length=240)
    summary: str | None = Field(default=None, max_length=2000)
    content_date: date | None = None
    blocks: tuple[EditorialBlock, ...] = ()


class EditorialValidationResponse(StrictModel):
    valid: bool
    violations: tuple[dict[str, object], ...] = ()


class EditorialRole(StrEnum):
    USER = "USER"
    EDITOR = "EDITOR"
    REVIEWER = "REVIEWER"
    ADMIN = "ADMIN"


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


class SeriesDownsampling(StrictModel):
    """Disclosure that ``points`` is an exact subset of the full series (ADR-013)."""

    method: Literal["M4"] = "M4"
    max_points: int = Field(ge=1)
    original_points: int = Field(ge=0)
    returned_points: int = Field(ge=0)
    preserved: tuple[Literal["FIRST", "LAST", "MIN", "MAX", "GAPS"], ...] = (
        "FIRST",
        "LAST",
        "MIN",
        "MAX",
        "GAPS",
    )
    basis: Literal["value"] = "value"


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
    downsampling: SeriesDownsampling | None = None
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


class EconomicEventImportance(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EconomicEventStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    RELEASED = "RELEASED"
    CANCELLED = "CANCELLED"
    UNAVAILABLE = "UNAVAILABLE"


class EconomicEventValueStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    PENDING = "PENDING"
    UNAVAILABLE = "UNAVAILABLE"


class EconomicCalendarProvenance(StrictModel):
    source: str
    dataset: str
    data_level: DataLevel
    freshness: Freshness
    source_timestamp: datetime | None = None
    collected_at: datetime
    timezone: str
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_demo_until_licensed(self) -> "EconomicCalendarProvenance":
        if self.data_level is not DataLevel.DEMO:
            raise ValueError("economic calendar remains DEMO until a provider is approved")
        if self.freshness is not Freshness.UNAVAILABLE and self.source_timestamp is None:
            raise ValueError("available calendar data requires source_timestamp")
        return self


class EconomicCalendarEvent(StrictModel):
    event_id: str
    event_key: str
    country: str = Field(pattern="^[A-Z]{2}$")
    timezone: str
    event_date: date
    event_time: datetime | None = None
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=1000)
    importance: EconomicEventImportance
    status: EconomicEventStatus
    value_status: EconomicEventValueStatus
    actual: Decimal | None = None
    forecast: Decimal | None = None
    previous: Decimal | None = None
    unit: str | None = Field(default=None, max_length=40)
    provenance: EconomicCalendarProvenance


class EconomicCalendarResponse(StrictModel):
    items: list[EconomicCalendarEvent]
    date_from: date
    date_to: date
    limit: int = Field(ge=1, le=100)


class BenchmarkItem(StrictModel):
    canonical_id: str
    symbol: str
    name: str
    currency: str = Field(pattern="^[A-Z]{3}$")
    value: Decimal | None = None
    change_percent: Decimal | None = None
    data_level: DataLevel
    freshness: Freshness
    source: str
    dataset: str
    timestamp_official: datetime | None = None
    timestamp_collected: datetime
    limitations: tuple[str, ...] = ()
    unavailable_reason: str | None = None


class BenchmarkListResponse(StrictModel):
    items: list[BenchmarkItem]


class BatchHistoryRequest(StrictModel):
    canonical_ids: list[str] = Field(min_length=1, max_length=10)
    period: HistoryPeriod = HistoryPeriod.ONE_M
    mode: SeriesMode = SeriesMode.INDEX_100
    adjustment_type: str = "UNADJUSTED"

    @model_validator(mode="after")
    def require_unique_ids(self) -> "BatchHistoryRequest":
        if len(set(self.canonical_ids)) != len(self.canonical_ids):
            raise ValueError("canonical_ids must be unique")
        return self


class BatchHistoryResponse(StrictModel):
    items: list[PublicHistorySeries]


class BatchQuoteRequest(StrictModel):
    canonical_ids: list[str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def require_unique_ids(self) -> "BatchQuoteRequest":
        if len(set(self.canonical_ids)) != len(self.canonical_ids):
            raise ValueError("canonical_ids must be unique")
        return self


class BatchQuoteResponse(StrictModel):
    items: list[PublicQuote]


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


class PerformanceStatus(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


class PerformanceProvenance(StrictModel):
    provider: str
    dataset: str
    source: str
    data_level: DataLevel
    freshness: Freshness
    source_timestamp: datetime
    collected_at: datetime
    latency_ms: int | None = Field(default=None, ge=0)
    limitations: tuple[str, ...] = ()


class PortfolioIncomeType(StrEnum):
    DIVIDEND = "DIVIDEND"
    JCP = "JCP"
    SPLIT = "SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"


class PortfolioIncomeStatus(StrEnum):
    APPLIED = "APPLIED"
    PENDING = "PENDING"
    UNAVAILABLE = "UNAVAILABLE"


class MarkerSourceType(StrEnum):
    LEDGER_EVENT = "LEDGER_EVENT"
    CORPORATE_ACTION = "CORPORATE_ACTION"


class PortfolioIncomeResponse(StrictModel):
    portfolio_id: str
    source_type: MarkerSourceType
    source_id: str
    canonical_id: str
    event_type: PortfolioIncomeType
    status: PortfolioIncomeStatus
    ex_date: date | None = None
    payment_date: date | None = None
    payer: str
    gross_amount_per_unit: Decimal | None = None
    net_amount_per_unit: Decimal | None = None
    quantity: Decimal | None = None
    currency: str | None = Field(default=None, pattern="^[A-Z]{3}$")
    split_ratio_from: Decimal | None = None
    split_ratio_to: Decimal | None = None
    provenance: PerformanceProvenance


class PortfolioEventMarkerResponse(StrictModel):
    portfolio_id: str
    source_type: MarkerSourceType
    source_id: str
    event_type: str
    canonical_id: str
    occurred_at: datetime
    quantity: Decimal | None = None
    amount: Decimal | None = None
    currency: str = Field(pattern="^[A-Z]{3}$")
    provenance: PerformanceProvenance


class PortfolioEventMarkersResponse(StrictModel):
    portfolio_id: str
    items: list[PortfolioEventMarkerResponse]


class WebVitalsMetric(StrEnum):
    LCP = "LCP"
    INP = "INP"
    CLS = "CLS"


class WebVitalsRequest(StrictModel):
    metric: WebVitalsMetric
    value: Decimal = Field(ge=0)
    route: str = Field(min_length=1, max_length=160, pattern=r"^/")
    sample_count: int = Field(default=1, ge=1, le=100000)
    observed_at: datetime | None = None

    @model_validator(mode="after")
    def require_aware_timestamp(self) -> "WebVitalsRequest":
        if self.observed_at is not None:
            if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
                raise ValueError("observed_at must be timezone-aware")
            self.observed_at = self.observed_at.astimezone(timezone.utc)
        return self


class WebVitalsAcceptedResponse(StrictModel):
    status: str = "accepted"
    metric: WebVitalsMetric
    route: str
    sample_count: int


class PortfolioValuationPositionResponse(StrictModel):
    canonical_id: str
    quantity: Decimal
    currency: str = Field(pattern="^[A-Z]{3}$")
    remaining_cost_basis: Decimal
    weighted_average_cost: Decimal
    price: Decimal | None = None
    market_value_native: Decimal | None = None
    market_value_base: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    fx_rate: Decimal | None = None
    status: PerformanceStatus
    missing_inputs: tuple[str, ...] = ()


class PortfolioValuationResponse(StrictModel):
    portfolio_id: str
    base_currency: str = Field(pattern="^[A-Z]{3}$")
    as_of: datetime
    cash_value_base: Decimal | None
    positions_value_base: Decimal | None
    total_value_base: Decimal | None
    realized_pnl: Decimal | None
    unrealized_pnl: Decimal | None
    status: PerformanceStatus
    missing_inputs: tuple[str, ...] = ()
    methodology: str
    provenance: tuple[PerformanceProvenance, ...] = ()
    positions: list[PortfolioValuationPositionResponse]


class EquityCurvePointResponse(StrictModel):
    valuation_date: date
    total_value_base: Decimal | None
    cash_value_base: Decimal | None
    positions_value_base: Decimal | None
    data_level: DataLevel
    freshness: Freshness
    valuation_status: PerformanceStatus
    missing_inputs: tuple[str, ...] = ()


class EquityCurveResponse(StrictModel):
    portfolio_id: str
    base_currency: str = Field(pattern="^[A-Z]{3}$")
    methodology: str
    points: list[EquityCurvePointResponse]
    provenance: tuple[PerformanceProvenance, ...] = ()


class PerformanceDecompositionResponse(StrictModel):
    portfolio_id: str
    base_currency: str = Field(pattern="^[A-Z]{3}$")
    price_effect: Decimal | None
    fx_effect: Decimal | None
    cash_flow_effect: Decimal | None
    fees_effect: Decimal | None
    income_effect: Decimal | None
    unclassified_or_unavailable: Decimal | None
    status: PerformanceStatus
    methodology: str
    missing_inputs: tuple[str, ...] = ()
    provenance: tuple[PerformanceProvenance, ...] = ()


class PortfolioPerformanceResponse(StrictModel):
    portfolio_id: str
    base_currency: str = Field(pattern="^[A-Z]{3}$")
    realized_pnl: Decimal | None
    unrealized_pnl: Decimal | None
    twr: Decimal | None
    status: PerformanceStatus
    methodology: str
    missing_inputs: tuple[str, ...] = ()
    provenance: tuple[PerformanceProvenance, ...] = ()


class ErrorProblem(StrictModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    request_id: str


class AdminHealthStatus(StrictModel):
    status: str = Field(pattern="^(ok|degraded|down)$")
    latency_ms: int | None = Field(default=None, ge=0)
    checked_at: datetime


class AdminContractStatus(StrictModel):
    version: str
    checked_at: datetime


class AdminBackfillStatus(StrictModel):
    status: str
    occurred_at: datetime
    job_id: str | None = None


class AdminStructuredError(StrictModel):
    code: str
    message: str
    occurred_at: datetime


class AdminBackgroundJobsStatus(StrictModel):
    last_refresh_at: datetime | None = None
    backfills: list[AdminBackfillStatus] = Field(default_factory=list)
    errors: list[AdminStructuredError] = Field(default_factory=list)
    checked_at: datetime


class AdminProviderStatus(StrictModel):
    provider: str
    dataset: str
    provider_status: str
    dataset_status: str
    license_status: str
    access: str = Field(pattern="^(allowed|denied)$")


class AdminProviderGovernanceStatus(StrictModel):
    items: list[AdminProviderStatus] = Field(default_factory=list)
    checked_at: datetime


class AdminQuarantineStatus(StrictModel):
    price_anomalies: int = Field(ge=0)
    corporate_actions: int = Field(ge=0)
    checked_at: datetime


class AdminLockStatus(StrictModel):
    name: str
    acquired_at: datetime
    ttl_seconds: int | None = Field(default=None, ge=0)


class AdminLocksStatus(StrictModel):
    items: list[AdminLockStatus] = Field(default_factory=list)
    checked_at: datetime


class AdminEditorialConsumptionStatus(StrictModel):
    last_published_at: datetime | None = None
    archived_versions: int = Field(ge=0)
    checked_at: datetime


class AdminVolumetricStatus(StrictModel):
    active_users: int = Field(ge=0)
    active_portfolios: int = Field(ge=0)
    checked_at: datetime


class AdminSystemResponse(StrictModel):
    request_id: str
    checked_at: datetime
    postgres: AdminHealthStatus
    redis: AdminHealthStatus
    openapi: AdminContractStatus
    background_jobs: AdminBackgroundJobsStatus
    providers: AdminProviderGovernanceStatus
    quarantine: AdminQuarantineStatus
    locks: AdminLocksStatus
    editorial: AdminEditorialConsumptionStatus
    volumetrics: AdminVolumetricStatus
