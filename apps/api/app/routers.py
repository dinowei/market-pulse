import json
import secrets
from datetime import date, timedelta
from uuid import uuid4

import psycopg
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)

from app.admin.system import build_admin_system
from app.auth.service import (
    AuthConflict,
    AuthInvalid,
    AuthRateLimited,
    AuthService,
    AuthUnavailable,
)
from app.contracts import (
    AdminSystemResponse,
    AuthUserResponse,
    BatchHistoryRequest,
    BatchHistoryResponse,
    BatchQuoteRequest,
    BatchQuoteResponse,
    BenchmarkListResponse,
    EconomicCalendarEvent,
    EconomicCalendarResponse,
    EconomicEventImportance,
    EditorialAdminPostListResponse,
    EditorialAdminPostResponse,
    EditorialPostCreateRequest,
    EditorialPostListResponse,
    EditorialPostResponse,
    EditorialRole,
    EditorialValidationResponse,
    EditorialVersionCreateRequest,
    EquityCurveResponse,
    HistoryPeriod,
    InstrumentList,
    InstrumentSummary,
    LoginRequest,
    PageMeta,
    PerformanceDecompositionResponse,
    PortfolioCashBalanceResponse,
    PortfolioCreateRequest,
    PortfolioEventMarkersResponse,
    PortfolioEventRequest,
    PortfolioEventResponse,
    PortfolioIncomeResponse,
    PortfolioListResponse,
    PortfolioPatchRequest,
    PortfolioPerformanceResponse,
    PortfolioPositionResponse,
    PortfolioResponse,
    PortfolioSummaryResponse,
    PortfolioValuationResponse,
    PublicHistorySeries,
    PublicQuote,
    RegisterRequest,
    SeriesDownsampling,
    SeriesMode,
    WatchlistCreateRequest,
    WatchlistItemCreateRequest,
    WatchlistItemResponse,
    WatchlistListResponse,
    WatchlistPatchRequest,
    WatchlistReorderRequest,
    WatchlistResponse,
    WebVitalsAcceptedResponse,
    WebVitalsRequest,
)
from app.core.config import get_settings, registration_open
from app.editorial.service import InMemoryEditorialService, PostgresEditorialService
from app.editorial.validator import EditorialStatus, validate_editorial_blocks
from app.errors import request_id as request_id_for
from app.instruments.catalog import (
    CatalogStatus,
    CoverageTier,
    DataSupportStatus,
    search_catalog,
)
from app.market_data.benchmarks import benchmark_items, benchmark_series
from app.market_data.downsampling import MAX_MAX_POINTS, MIN_MAX_POINTS, downsample_m4
from app.market_data.economic_calendar import (
    CALENDAR_LIMIT,
    CALENDAR_MAX_DAYS,
    filter_events,
    valid_timezone,
)
from app.market_data.normalization import AdjustmentType
from app.market_data.public_market_data import public_history, public_quote
from app.market_data.refresh_application import (
    RefreshBatchRequest,
    RefreshBatchResponse,
    refresh_market_data,
)
from app.portfolios.day27 import (
    PortfolioReadModelNotFound,
    PostgresPortfolioDay27Service,
)
from app.portfolios.performance import PortfolioPerformanceService
from app.portfolios.service import (
    PortfolioConflict,
    PortfolioNotFound,
    PortfolioService,
    PortfolioValidationError,
    PostgresPortfolioService,
)
from app.telemetry import PostgresWebVitalsService, validate_web_vitals_payload
from app.watchlists.service import (
    PostgresWatchlistService,
    WatchlistConflict,
    WatchlistInvalid,
    WatchlistNotFound,
)

router = APIRouter(prefix="/api/v1")


def get_auth_service() -> AuthService:
    return AuthService()


def get_watchlist_service() -> PostgresWatchlistService:
    return PostgresWatchlistService()


def get_portfolio_service() -> PortfolioService:
    return PostgresPortfolioService()


def get_portfolio_performance_service() -> PortfolioPerformanceService:
    return PortfolioPerformanceService(PostgresPortfolioService())


def get_portfolio_day27_service() -> PostgresPortfolioDay27Service:
    return PostgresPortfolioDay27Service()


def get_web_vitals_service() -> PostgresWebVitalsService:
    return PostgresWebVitalsService()


def get_editorial_service() -> InMemoryEditorialService:
    return PostgresEditorialService()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _auth_error(request: Request, error: Exception) -> HTTPException:
    if isinstance(error, AuthConflict):
        return HTTPException(status_code=409, detail="Unable to register with supplied credentials")
    if isinstance(error, AuthRateLimited):
        return HTTPException(status_code=429, detail="Too many authentication attempts")
    if isinstance(error, AuthUnavailable):
        return HTTPException(status_code=503, detail="Authentication service unavailable")
    return HTTPException(status_code=401, detail="Invalid authentication credentials")


@router.post(
    "/auth/register",
    response_model=AuthUserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
def register(payload: RegisterRequest, request: Request) -> AuthUserResponse:
    if not registration_open(get_settings()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    try:
        return get_auth_service().register(payload, _client_ip(request))
    except (AuthConflict, AuthRateLimited, AuthUnavailable) as exc:
        raise _auth_error(request, exc) from exc


@router.post("/auth/login", response_model=AuthUserResponse, tags=["auth"])
def login(payload: LoginRequest, request: Request, response: Response) -> AuthUserResponse:
    try:
        user, token, _expires_at = get_auth_service().login(payload, _client_ip(request))
    except (AuthInvalid, AuthRateLimited, AuthUnavailable) as exc:
        raise _auth_error(request, exc) from exc
    settings = get_settings()
    secure = settings.auth_cookie_secure or settings.environment not in {"local", "test"}
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.auth_session_ttl_seconds,
        path="/",
    )
    return user


def get_current_user(
    request: Request, session_token: str | None = Cookie(default=None, alias="market_pulse_session")
) -> AuthUserResponse:
    # Already validated in this request by the rate-limit middleware (H-19, ADR-017).
    cached = getattr(request.state, "authenticated_user", None)
    if isinstance(cached, AuthUserResponse):
        return cached
    service = get_auth_service()
    cookie_name = get_settings().auth_cookie_name
    if cookie_name != "market_pulse_session":
        session_token = request.cookies.get(cookie_name)
    try:
        return service.me(session_token)
    except (AuthInvalid, AuthUnavailable) as exc:
        raise _auth_error(request, exc) from exc


def get_editorial_role(
    current_user: AuthUserResponse = Depends(get_current_user),
) -> str:
    try:
        with psycopg.connect(get_settings().database_url) as conn:
            row = conn.execute("SELECT role FROM users WHERE id=%s", (current_user.id,)).fetchone()
        return str(row[0]) if row and row[0] else EditorialRole.USER.value
    except Exception:
        return EditorialRole.USER.value


def _require_editorial_role(role: str, *allowed: EditorialRole) -> None:
    if role not in {item.value for item in allowed}:
        raise HTTPException(status_code=403, detail="Editorial permission required")


def _admin_role_for_user(user_id: str) -> str:
    try:
        with psycopg.connect(
            get_settings().database_url,
            connect_timeout=max(1, int(get_settings().database_timeout_seconds)),
        ) as conn:
            row = conn.execute("SELECT role FROM users WHERE id=%s", (user_id,)).fetchone()
        return str(row[0]) if row and row[0] else EditorialRole.USER.value
    except Exception:
        return EditorialRole.USER.value


def _record_admin_audit(
    *,
    actor_user_id: str | None,
    action: str,
    resource: str,
    result: str,
    request_id: str,
) -> None:
    try:
        with psycopg.connect(
            get_settings().database_url,
            connect_timeout=max(1, int(get_settings().database_timeout_seconds)),
        ) as conn:
            conn.execute(
                "INSERT INTO audit_logs "
                "(entity_type, action, actor_user_id, occurred_at, metadata, resource, "
                "result, request_id) "
                "VALUES (%s, %s, %s, now(), %s::jsonb, %s, %s, %s)",
                (
                    "admin_system",
                    action,
                    actor_user_id,
                    json.dumps(
                        {
                            "actor": actor_user_id or "anonymous",
                            "resource": resource,
                            "result": result,
                            "request_id": request_id,
                        }
                    ),
                    resource,
                    result,
                    request_id,
                ),
            )
            conn.commit()
    except Exception:
        # Operational visibility must never expose database details or break auth.
        return


def get_admin_user(
    request: Request,
    session_token: str | None = Cookie(default=None, alias="market_pulse_session"),
) -> AuthUserResponse:
    request_id = request_id_for(request)
    try:
        current_user = get_current_user(request, session_token)
    except HTTPException:
        _record_admin_audit(
            actor_user_id=None,
            action="view_admin_system",
            resource="/admin/system",
            result="denied",
            request_id=request_id,
        )
        raise
    role = _admin_role_for_user(current_user.id)
    if role != EditorialRole.ADMIN.value:
        _record_admin_audit(
            actor_user_id=current_user.id,
            action="view_admin_system",
            resource="/admin/system",
            result="denied",
            request_id=request_id,
        )
        raise HTTPException(status_code=403, detail="Admin permission required")
    _record_admin_audit(
        actor_user_id=current_user.id,
        action="view_admin_system",
        resource="/admin/system",
        result="allowed",
        request_id=request_id,
    )
    return current_user


@router.get(
    "/admin/system",
    response_model=AdminSystemResponse,
    tags=["admin-system"],
)
def admin_system(
    request: Request,
    _admin: AuthUserResponse = Depends(get_admin_user),
) -> AdminSystemResponse:
    return build_admin_system(request_id_for(request))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
def logout(
    request: Request,
    response: Response,
    session_token: str | None = Cookie(default=None, alias="market_pulse_session"),
) -> None:
    service = get_auth_service()
    cookie_name = get_settings().auth_cookie_name
    token = (
        request.cookies.get(cookie_name) if cookie_name != "market_pulse_session" else session_token
    )
    try:
        service.logout(token)
    except AuthUnavailable as exc:
        raise _auth_error(request, exc) from exc
    response.delete_cookie(cookie_name, path="/")


@router.get("/auth/me", response_model=AuthUserResponse, tags=["auth"])
def me(
    request: Request, session_token: str | None = Cookie(default=None, alias="market_pulse_session")
) -> AuthUserResponse:
    return get_current_user(request, session_token)


def _authorize_internal_refresh(provided: str | None, expected: str | None) -> bool:
    if not expected or not provided:
        return False
    return secrets.compare_digest(provided, expected)


@router.post(
    "/internal/refresh-quotes",
    response_model=RefreshBatchResponse,
    tags=["internal"],
)
def internal_refresh_quotes(
    payload: RefreshBatchRequest,
    request: Request,
    cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
) -> RefreshBatchResponse:
    settings = get_settings()
    if not _authorize_internal_refresh(cron_secret, settings.internal_refresh_secret):
        raise HTTPException(status_code=401, detail="Internal refresh unauthorized")
    max_items = payload.max_items or settings.refresh_max_items
    if (
        max_items > settings.refresh_max_items
        or len(payload.canonical_ids) > settings.refresh_max_items
    ):
        raise HTTPException(status_code=422, detail="Refresh batch exceeds configured limit")
    return refresh_market_data(
        payload=payload,
        settings=settings,
        request_id=request_id_for(request),
    )


@router.get("/instruments", response_model=InstrumentList, tags=["instruments"])
def list_instruments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: str = Query("created_at"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
) -> InstrumentList:
    if sort not in {"created_at", "symbol", "name"}:
        raise HTTPException(status_code=422, detail="Unsupported sort field")
    return InstrumentList(items=[], meta=PageMeta(limit=limit, offset=offset, next_offset=None))


@router.get("/instruments/search", response_model=InstrumentList, tags=["instruments"])
def search_instruments(
    q: str = Query(..., min_length=1, max_length=64),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> InstrumentList:
    entries = search_catalog(q)
    page = entries[offset : offset + limit]
    items = [
        InstrumentSummary(
            id=entry.canonical_id,
            canonical_id=entry.canonical_id,
            symbol=entry.symbol,
            display_symbol=entry.display_symbol,
            name=entry.name,
            instrument_type=entry.instrument_type,
            currency=entry.currency,
            aliases=entry.aliases,
            catalog_status=entry.catalog_status.value,
            coverage_tier=entry.coverage_tier.value,
            data_support_status=entry.data_support_status.value,
            support_state=(
                "BLOCKED_SCOPE"
                if entry.catalog_status is CatalogStatus.OUT_OF_SCOPE
                else "UNSUPPORTED"
                if entry.data_support_status is DataSupportStatus.UNAVAILABLE
                else "CANDIDATE_FUTURE"
                if entry.coverage_tier is not CoverageTier.P0_OPERATIONAL
                else "P0_OPERATIONAL"
            ),
        )
        for entry in page
    ]
    next_offset = offset + limit if offset + limit < len(entries) else None
    return InstrumentList(
        items=items,
        meta=PageMeta(limit=limit, offset=offset, next_offset=next_offset),
    )


@router.get("/market-data/quotes/latest", tags=["market-data"])
def latest_quote() -> dict[str, object]:
    return {"items": [], "status": "UNAVAILABLE", "reason": "LICENSE_BLOCKED"}


@router.get(
    "/market-data/quotes/{canonical_id}",
    response_model=PublicQuote,
    tags=["market-data"],
)
def public_quote_by_id(canonical_id: str, request: Request) -> PublicQuote:
    try:
        return public_quote(canonical_id, request_id_for(request))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Instrument not found") from exc


@router.post(
    "/market-data/quotes/batch",
    response_model=BatchQuoteResponse,
    tags=["market-data"],
)
def public_quotes_batch(payload: BatchQuoteRequest, request: Request) -> BatchQuoteResponse:
    items: list[PublicQuote] = []
    for canonical_id in payload.canonical_ids:
        try:
            items.append(public_quote(canonical_id, request_id_for(request)))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Instrument not found") from exc
    return BatchQuoteResponse(items=items)


@router.get(
    "/market-data/benchmarks",
    response_model=BenchmarkListResponse,
    tags=["market-data", "benchmarks"],
)
def public_benchmarks() -> BenchmarkListResponse:
    return BenchmarkListResponse(items=benchmark_items())


@router.get(
    "/market-data/history/{canonical_id}",
    response_model=PublicHistorySeries,
    tags=["market-data"],
)
def public_history_by_id(
    canonical_id: str,
    request: Request,
    period: HistoryPeriod = Query(...),
    mode: SeriesMode = Query(SeriesMode.PRICE),
    adjustment_type: AdjustmentType = Query(AdjustmentType.UNADJUSTED),
    max_points: int | None = Query(
        None,
        ge=MIN_MAX_POINTS,
        le=MAX_MAX_POINTS,
        description=(
            "Opt-in display reduction (M4): keeps first, last, min, max per bucket and every "
            "gap; points stay an exact subset. Omit for the full series."
        ),
    ),
) -> PublicHistorySeries:
    series = benchmark_series(canonical_id, period, mode, request_id_for(request))
    if series is None:
        try:
            series = public_history(
                canonical_id,
                period,
                mode,
                request_id_for(request),
                adjustment_type.value,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Instrument not found") from exc
    return _with_display_downsampling(series, max_points)


def _with_display_downsampling(
    series: PublicHistorySeries, max_points: int | None
) -> PublicHistorySeries:
    if max_points is None:
        return series
    reduced = downsample_m4(series.points, max_points)
    if not reduced.applied:
        return series
    return series.model_copy(
        update={
            "points": reduced.points,
            "downsampling": SeriesDownsampling(
                max_points=max_points,
                original_points=reduced.original_points,
                returned_points=len(reduced.points),
            ),
        }
    )


@router.post(
    "/market-data/history/batch",
    response_model=BatchHistoryResponse,
    tags=["market-data"],
)
def public_history_batch(
    payload: BatchHistoryRequest,
    request: Request,
) -> BatchHistoryResponse:
    request_id = request_id_for(request)
    items: list[PublicHistorySeries] = []
    for canonical_id in payload.canonical_ids:
        benchmark = benchmark_series(canonical_id, payload.period, payload.mode, request_id)
        if benchmark is not None:
            items.append(benchmark)
            continue
        try:
            items.append(
                public_history(
                    canonical_id,
                    payload.period,
                    payload.mode,
                    request_id,
                    payload.adjustment_type,
                )
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Instrument not found") from exc
    return BatchHistoryResponse(items=items)


@router.get(
    "/economic-calendar",
    response_model=EconomicCalendarResponse,
    tags=["economic-calendar"],
)
def economic_calendar(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    country: str | None = Query(default=None, min_length=2, max_length=2, pattern="^[A-Z]{2}$"),
    timezone_name: str | None = Query(default=None, alias="timezone"),
    importance: EconomicEventImportance | None = Query(default=None),
    limit: int = Query(default=CALENDAR_LIMIT, ge=1, le=CALENDAR_LIMIT),
) -> EconomicCalendarResponse:
    today = date.today()
    start = date_from or today
    end = date_to or start + timedelta(days=30)
    if end < start:
        raise HTTPException(status_code=422, detail="date_to must be on or after date_from")
    if (end - start).days > CALENDAR_MAX_DAYS:
        raise HTTPException(
            status_code=422,
            detail=f"economic calendar range cannot exceed {CALENDAR_MAX_DAYS} days",
        )
    if timezone_name and not valid_timezone(timezone_name):
        raise HTTPException(status_code=422, detail="timezone must be a valid IANA timezone")
    items = filter_events(
        date_from=start,
        date_to=end,
        country=country,
        importance=importance,
        timezone_name=timezone_name,
    )[:limit]
    return EconomicCalendarResponse(items=items, date_from=start, date_to=end, limit=limit)


@router.get(
    "/economic-calendar/{event_id}",
    response_model=EconomicCalendarEvent,
    tags=["economic-calendar"],
)
def economic_calendar_detail(event_id: str) -> EconomicCalendarEvent:
    today = date.today()
    for event in filter_events(
        date_from=today - timedelta(days=1),
        date_to=today + timedelta(days=366),
    ):
        if event.event_id == event_id:
            return event
    raise HTTPException(status_code=404, detail="Economic event not found")


@router.get("/market-data/series", tags=["market-data"])
def historical_series() -> dict[str, list]:
    return {"items": []}


def _watchlist_error(error: Exception) -> HTTPException:
    if isinstance(error, WatchlistConflict):
        return HTTPException(status_code=409, detail="Watchlist already exists")
    if isinstance(error, WatchlistNotFound):
        return HTTPException(status_code=404, detail="Watchlist or item not found")
    return HTTPException(status_code=422, detail=str(error))


def _portfolio_error(error: Exception) -> HTTPException:
    if isinstance(error, PortfolioNotFound):
        return HTTPException(status_code=404, detail="Portfolio or event not found")
    if isinstance(error, PortfolioConflict):
        return HTTPException(status_code=409, detail=str(error))
    return HTTPException(status_code=422, detail=str(error))


@router.get("/watchlists", response_model=WatchlistListResponse, tags=["watchlists"])
def list_watchlists(
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PostgresWatchlistService = Depends(get_watchlist_service),
) -> WatchlistListResponse:
    return WatchlistListResponse(items=service.list(current_user.id))


@router.post(
    "/watchlists",
    response_model=WatchlistResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["watchlists"],
)
def create_watchlist(
    payload: WatchlistCreateRequest,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PostgresWatchlistService = Depends(get_watchlist_service),
) -> WatchlistResponse:
    try:
        return service.create(current_user.id, payload.name)
    except (WatchlistConflict, WatchlistNotFound, WatchlistInvalid) as exc:
        raise _watchlist_error(exc) from exc


@router.get("/watchlists/{watchlist_id}", response_model=WatchlistResponse, tags=["watchlists"])
def get_watchlist(
    watchlist_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PostgresWatchlistService = Depends(get_watchlist_service),
) -> WatchlistResponse:
    try:
        return service.get(current_user.id, watchlist_id)
    except WatchlistNotFound as exc:
        raise _watchlist_error(exc) from exc


@router.patch("/watchlists/{watchlist_id}", response_model=WatchlistResponse, tags=["watchlists"])
def rename_watchlist(
    watchlist_id: str,
    payload: WatchlistPatchRequest,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PostgresWatchlistService = Depends(get_watchlist_service),
) -> WatchlistResponse:
    try:
        return service.rename(current_user.id, watchlist_id, payload.name)
    except (WatchlistConflict, WatchlistNotFound, WatchlistInvalid) as exc:
        raise _watchlist_error(exc) from exc


@router.delete(
    "/watchlists/{watchlist_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["watchlists"],
)
def delete_watchlist(
    watchlist_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PostgresWatchlistService = Depends(get_watchlist_service),
) -> None:
    try:
        service.delete(current_user.id, watchlist_id)
    except (WatchlistNotFound, WatchlistInvalid) as exc:
        raise _watchlist_error(exc) from exc


@router.post(
    "/watchlists/{watchlist_id}/items",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["watchlists"],
)
def add_watchlist_item(
    watchlist_id: str,
    payload: WatchlistItemCreateRequest,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PostgresWatchlistService = Depends(get_watchlist_service),
) -> WatchlistItemResponse:
    try:
        item = service.add_item(current_user.id, watchlist_id, payload.canonical_id)
        return item
    except (WatchlistNotFound, WatchlistInvalid) as exc:
        if isinstance(exc, WatchlistInvalid) and "already" in str(exc).lower():
            return service.add_item(current_user.id, watchlist_id, payload.canonical_id)
        raise _watchlist_error(exc) from exc


@router.delete(
    "/watchlists/{watchlist_id}/items/{canonical_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["watchlists"],
)
def remove_watchlist_item(
    watchlist_id: str,
    canonical_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PostgresWatchlistService = Depends(get_watchlist_service),
) -> None:
    try:
        service.remove_item(current_user.id, watchlist_id, canonical_id)
    except (WatchlistNotFound, WatchlistInvalid) as exc:
        raise _watchlist_error(exc) from exc


@router.patch(
    "/watchlists/{watchlist_id}/items/reorder",
    response_model=WatchlistResponse,
    tags=["watchlists"],
)
def reorder_watchlist_items(
    watchlist_id: str,
    payload: WatchlistReorderRequest,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PostgresWatchlistService = Depends(get_watchlist_service),
) -> WatchlistResponse:
    try:
        return service.reorder(current_user.id, watchlist_id, payload.canonical_ids)
    except (WatchlistNotFound, WatchlistInvalid) as exc:
        raise _watchlist_error(exc) from exc


@router.post(
    "/watchlists/favorites/{canonical_id}",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["watchlists"],
)
def favorite_instrument(
    canonical_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PostgresWatchlistService = Depends(get_watchlist_service),
) -> WatchlistItemResponse:
    try:
        return service.favorite(current_user.id, canonical_id)
    except (WatchlistNotFound, WatchlistInvalid) as exc:
        raise _watchlist_error(exc) from exc


@router.delete(
    "/watchlists/favorites/{canonical_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["watchlists"],
)
def unfavorite_instrument(
    canonical_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PostgresWatchlistService = Depends(get_watchlist_service),
) -> None:
    try:
        service.unfavorite(current_user.id, canonical_id)
    except (WatchlistNotFound, WatchlistInvalid) as exc:
        raise _watchlist_error(exc) from exc


@router.get("/portfolios", response_model=PortfolioListResponse, tags=["portfolios"])
def list_portfolios(
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioListResponse:
    return service.list(current_user.id)


@router.post(
    "/portfolios",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["portfolios"],
)
def create_portfolio(
    payload: PortfolioCreateRequest,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioResponse:
    try:
        return service.create(current_user.id, payload)
    except (PortfolioConflict, PortfolioValidationError) as exc:
        raise _portfolio_error(exc) from exc


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioResponse, tags=["portfolios"])
def get_portfolio(
    portfolio_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioResponse:
    try:
        return service.get(current_user.id, portfolio_id)
    except PortfolioNotFound as exc:
        raise _portfolio_error(exc) from exc


@router.patch("/portfolios/{portfolio_id}", response_model=PortfolioResponse, tags=["portfolios"])
def patch_portfolio(
    portfolio_id: str,
    payload: PortfolioPatchRequest,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioResponse:
    try:
        return service.patch(current_user.id, portfolio_id, payload)
    except (PortfolioNotFound, PortfolioConflict, PortfolioValidationError) as exc:
        raise _portfolio_error(exc) from exc


@router.post(
    "/portfolios/{portfolio_id}/events",
    response_model=PortfolioEventResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["portfolios"],
)
def add_portfolio_event(
    portfolio_id: str,
    payload: PortfolioEventRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioEventResponse:
    if not idempotency_key:
        raise HTTPException(status_code=422, detail="Idempotency-Key header is required")
    try:
        return service.add_event(
            current_user.id,
            portfolio_id,
            payload,
            idempotency_key,
            request_id_for(request),
        )
    except (PortfolioNotFound, PortfolioConflict, PortfolioValidationError, ValueError) as exc:
        raise _portfolio_error(exc) from exc


@router.get(
    "/portfolios/{portfolio_id}/events",
    response_model=list[PortfolioEventResponse],
    tags=["portfolios"],
)
def list_portfolio_events(
    portfolio_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> list[PortfolioEventResponse]:
    try:
        return service.events(current_user.id, portfolio_id)
    except PortfolioNotFound as exc:
        raise _portfolio_error(exc) from exc


@router.get(
    "/portfolios/{portfolio_id}/positions",
    response_model=list[PortfolioPositionResponse],
    tags=["portfolios"],
)
def list_portfolio_positions(
    portfolio_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> list[PortfolioPositionResponse]:
    try:
        return service.positions(current_user.id, portfolio_id)
    except PortfolioNotFound as exc:
        raise _portfolio_error(exc) from exc


@router.get(
    "/portfolios/{portfolio_id}/cash-balances",
    response_model=list[PortfolioCashBalanceResponse],
    tags=["portfolios"],
)
def list_portfolio_cash_balances(
    portfolio_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> list[PortfolioCashBalanceResponse]:
    try:
        return service.cash_balances(current_user.id, portfolio_id)
    except PortfolioNotFound as exc:
        raise _portfolio_error(exc) from exc


@router.get(
    "/portfolios/{portfolio_id}/summary",
    response_model=PortfolioSummaryResponse,
    tags=["portfolios"],
)
def portfolio_summary(
    portfolio_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioSummaryResponse:
    try:
        return service.summary(current_user.id, portfolio_id)
    except PortfolioNotFound as exc:
        raise _portfolio_error(exc) from exc


@router.post(
    "/portfolios/{portfolio_id}/events/{event_id}/reversal",
    response_model=PortfolioEventResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["portfolios"],
)
def reverse_portfolio_event(
    portfolio_id: str,
    event_id: str,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioEventResponse:
    if not idempotency_key:
        raise HTTPException(status_code=422, detail="Idempotency-Key header is required")
    try:
        return service.reverse_event(
            current_user.id,
            portfolio_id,
            event_id,
            idempotency_key,
            request_id_for(request),
        )
    except (PortfolioNotFound, PortfolioConflict, PortfolioValidationError) as exc:
        raise _portfolio_error(exc) from exc


@router.get(
    "/portfolios/{portfolio_id}/valuation",
    response_model=PortfolioValuationResponse,
    tags=["portfolio-performance"],
)
def portfolio_valuation(
    portfolio_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioPerformanceService = Depends(get_portfolio_performance_service),
) -> PortfolioValuationResponse:
    try:
        return service.valuation_response(current_user.id, portfolio_id)
    except PortfolioNotFound as exc:
        raise _portfolio_error(exc) from exc


@router.get(
    "/portfolios/{portfolio_id}/performance",
    response_model=PortfolioPerformanceResponse,
    tags=["portfolio-performance"],
)
def portfolio_performance(
    portfolio_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioPerformanceService = Depends(get_portfolio_performance_service),
) -> PortfolioPerformanceResponse:
    try:
        return service.performance_response(current_user.id, portfolio_id)
    except PortfolioNotFound as exc:
        raise _portfolio_error(exc) from exc


@router.get(
    "/portfolios/{portfolio_id}/equity-curve",
    response_model=EquityCurveResponse,
    tags=["portfolio-performance"],
)
def portfolio_equity_curve(
    portfolio_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioPerformanceService = Depends(get_portfolio_performance_service),
) -> EquityCurveResponse:
    try:
        return service.equity_curve_response(current_user.id, portfolio_id)
    except PortfolioNotFound as exc:
        raise _portfolio_error(exc) from exc


@router.get(
    "/portfolios/{portfolio_id}/performance/decomposition",
    response_model=PerformanceDecompositionResponse,
    tags=["portfolio-performance"],
)
def portfolio_performance_decomposition(
    portfolio_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PortfolioPerformanceService = Depends(get_portfolio_performance_service),
) -> PerformanceDecompositionResponse:
    try:
        return service.decomposition_response(current_user.id, portfolio_id)
    except PortfolioNotFound as exc:
        raise _portfolio_error(exc) from exc


@router.get(
    "/portfolios/{portfolio_id}/income",
    response_model=list[PortfolioIncomeResponse],
    tags=["portfolio-income"],
)
def portfolio_income(
    portfolio_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PostgresPortfolioDay27Service = Depends(get_portfolio_day27_service),
) -> list[PortfolioIncomeResponse]:
    try:
        return service.income(current_user.id, portfolio_id)
    except PortfolioReadModelNotFound as exc:
        raise _portfolio_error(PortfolioNotFound()) from exc


@router.get(
    "/portfolios/{portfolio_id}/event-markers",
    response_model=PortfolioEventMarkersResponse,
    tags=["portfolio-performance"],
)
def portfolio_event_markers(
    portfolio_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    service: PostgresPortfolioDay27Service = Depends(get_portfolio_day27_service),
) -> PortfolioEventMarkersResponse:
    try:
        return service.markers(current_user.id, portfolio_id)
    except PortfolioReadModelNotFound as exc:
        raise _portfolio_error(PortfolioNotFound()) from exc


@router.post(
    "/telemetry/web-vitals",
    response_model=WebVitalsAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["telemetry"],
)
def record_web_vitals(
    payload: WebVitalsRequest,
    service: PostgresWebVitalsService = Depends(get_web_vitals_service),
) -> WebVitalsAcceptedResponse:
    aggregate = validate_web_vitals_payload(payload.model_dump(mode="json"))
    service.record(aggregate)
    return WebVitalsAcceptedResponse(
        metric=payload.metric,
        route=payload.route,
        sample_count=payload.sample_count,
    )


@router.get("/performance", tags=["performance"])
def performance() -> dict[str, list]:
    return {"items": []}


def _editorial_response(post) -> EditorialPostResponse:
    if post is None or post.status is not EditorialStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Editorial post not found")
    return EditorialPostResponse(
        id=post.id,
        slug=post.slug,
        title=post.title,
        summary=post.summary,
        content_date=post.content_date,
        blocks=post.blocks,
        status=post.status,
        version=post.version,
        created_at=post.created_at,
        published_at=post.published_at,
    )


@router.get(
    "/editorial/morning-call/latest",
    response_model=EditorialPostResponse,
    tags=["editorial"],
)
def latest_morning_call(
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialPostResponse:
    return _editorial_response(service.latest_published())


@router.get(
    "/editorial/posts",
    response_model=EditorialPostListResponse,
    tags=["editorial"],
)
def list_editorial_posts(
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialPostListResponse:
    return EditorialPostListResponse(
        items=[_editorial_response(post) for post in service.list_published()]
    )


@router.get(
    "/editorial/posts/{slug}",
    response_model=EditorialPostResponse,
    tags=["editorial"],
)
def get_editorial_post(
    slug: str,
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialPostResponse:
    return _editorial_response(service.get_published(slug))


def _admin_response(post) -> EditorialAdminPostResponse:
    return EditorialAdminPostResponse(
        id=post.id,
        slug=post.slug,
        title=post.title,
        summary=post.summary,
        content_date=post.content_date,
        blocks=post.blocks,
        status=post.status,
        version=post.version,
        created_at=post.created_at,
        published_at=post.published_at,
    )


@router.get(
    "/editorial/admin/posts",
    response_model=EditorialAdminPostListResponse,
    tags=["editorial-admin"],
)
def admin_list_editorial_posts(
    current_user: AuthUserResponse = Depends(get_current_user),
    role: str = Depends(get_editorial_role),
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialAdminPostListResponse:
    _require_editorial_role(role, EditorialRole.EDITOR, EditorialRole.REVIEWER, EditorialRole.ADMIN)
    return EditorialAdminPostListResponse(
        items=[_admin_response(post) for post in service.list_admin()]
    )


@router.post(
    "/editorial/admin/posts",
    response_model=EditorialAdminPostResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["editorial-admin"],
)
def admin_create_editorial_post(
    payload: EditorialPostCreateRequest,
    request: Request,
    current_user: AuthUserResponse = Depends(get_current_user),
    role: str = Depends(get_editorial_role),
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialAdminPostResponse:
    _require_editorial_role(role, EditorialRole.EDITOR, EditorialRole.ADMIN)
    try:
        return _admin_response(
            service.create_draft(
                slug=payload.slug,
                title=payload.title,
                summary=payload.summary,
                blocks=payload.blocks,
                content_date=payload.content_date,
                created_by_user_id=current_user.id,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/editorial/admin/posts/{post_id}",
    response_model=EditorialAdminPostResponse,
    tags=["editorial-admin"],
)
def admin_get_editorial_post(
    post_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    role: str = Depends(get_editorial_role),
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialAdminPostResponse:
    _require_editorial_role(role, EditorialRole.EDITOR, EditorialRole.REVIEWER, EditorialRole.ADMIN)
    try:
        return _admin_response(service.get_by_id(post_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Editorial post not found") from exc


@router.post(
    "/editorial/admin/posts/{post_id}/versions",
    response_model=EditorialAdminPostResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["editorial-admin"],
)
def admin_add_editorial_version(
    post_id: str,
    payload: EditorialVersionCreateRequest,
    current_user: AuthUserResponse = Depends(get_current_user),
    role: str = Depends(get_editorial_role),
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialAdminPostResponse:
    _require_editorial_role(role, EditorialRole.EDITOR, EditorialRole.ADMIN)
    try:
        return _admin_response(
            service.add_version(
                post_id,
                title=payload.title,
                summary=payload.summary,
                blocks=payload.blocks,
                content_date=payload.content_date,
            )
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Editorial post not found") from exc


@router.post(
    "/editorial/admin/posts/{post_id}/validate",
    response_model=EditorialValidationResponse,
    tags=["editorial-admin"],
)
def admin_validate_editorial_post(
    post_id: str,
    current_user: AuthUserResponse = Depends(get_current_user),
    role: str = Depends(get_editorial_role),
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialValidationResponse:
    _require_editorial_role(role, EditorialRole.EDITOR, EditorialRole.REVIEWER, EditorialRole.ADMIN)
    try:
        post = service.get_by_id(post_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Editorial post not found") from exc
    report = validate_editorial_blocks(post.blocks)
    return EditorialValidationResponse(
        valid=report.valid,
        violations=tuple(item.model_dump() for item in report.violations),
    )


def _admin_transition(
    post_id: str,
    target: EditorialStatus,
    role: str,
    service: InMemoryEditorialService,
    current_user: AuthUserResponse,
    request: Request,
) -> EditorialAdminPostResponse:
    allowed = {
        EditorialStatus.UNDER_REVIEW: (EditorialRole.EDITOR, EditorialRole.ADMIN),
        EditorialStatus.APPROVED: (EditorialRole.REVIEWER, EditorialRole.ADMIN),
        EditorialStatus.PUBLISHED: (EditorialRole.REVIEWER, EditorialRole.ADMIN),
        EditorialStatus.ARCHIVED: (EditorialRole.REVIEWER, EditorialRole.ADMIN),
    }
    _require_editorial_role(role, *allowed[target])
    try:
        return _admin_response(
            service.transition_by_id(
                post_id,
                target,
                actor_user_id=current_user.id,
                request_id=request_id_for(request),
            )
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Editorial post not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/editorial/admin/posts/{post_id}/submit-review",
    response_model=EditorialAdminPostResponse,
    tags=["editorial-admin"],
)
def admin_submit_review(
    post_id: str,
    request: Request,
    current_user: AuthUserResponse = Depends(get_current_user),
    role: str = Depends(get_editorial_role),
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialAdminPostResponse:
    return _admin_transition(
        post_id, EditorialStatus.UNDER_REVIEW, role, service, current_user, request
    )


@router.post(
    "/editorial/admin/posts/{post_id}/approve",
    response_model=EditorialAdminPostResponse,
    tags=["editorial-admin"],
)
def admin_approve(
    post_id: str,
    request: Request,
    current_user: AuthUserResponse = Depends(get_current_user),
    role: str = Depends(get_editorial_role),
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialAdminPostResponse:
    return _admin_transition(
        post_id, EditorialStatus.APPROVED, role, service, current_user, request
    )


@router.post(
    "/editorial/admin/posts/{post_id}/publish",
    response_model=EditorialAdminPostResponse,
    tags=["editorial-admin"],
)
def admin_publish(
    post_id: str,
    request: Request,
    current_user: AuthUserResponse = Depends(get_current_user),
    role: str = Depends(get_editorial_role),
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialAdminPostResponse:
    return _admin_transition(
        post_id, EditorialStatus.PUBLISHED, role, service, current_user, request
    )


@router.post(
    "/editorial/admin/posts/{post_id}/archive",
    response_model=EditorialAdminPostResponse,
    tags=["editorial-admin"],
)
def admin_archive(
    post_id: str,
    request: Request,
    current_user: AuthUserResponse = Depends(get_current_user),
    role: str = Depends(get_editorial_role),
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialAdminPostResponse:
    return _admin_transition(
        post_id, EditorialStatus.ARCHIVED, role, service, current_user, request
    )


@router.get(
    "/editorial/posts/{slug}/versions", response_model=EditorialPostListResponse, tags=["editorial"]
)
def public_editorial_versions(
    slug: str, service: InMemoryEditorialService = Depends(get_editorial_service)
) -> EditorialPostListResponse:
    versions = service.public_versions(slug)
    if not versions:
        raise HTTPException(status_code=404, detail="Editorial post not found")
    return EditorialPostListResponse(items=[_editorial_response(version) for version in versions])


@router.get(
    "/editorial/posts/{slug}/versions/{version_number}",
    response_model=EditorialPostResponse,
    tags=["editorial"],
)
def public_editorial_version(
    slug: str,
    version_number: int,
    service: InMemoryEditorialService = Depends(get_editorial_service),
) -> EditorialPostResponse:
    version = next(
        (item for item in service.public_versions(slug) if item.version == version_number), None
    )
    return _editorial_response(version)


def _record_account_audit(
    *,
    actor_user_id: str,
    action: str,
    resource: str,
    result: str,
    request_id: str,
    metadata: dict | None = None,
) -> None:
    try:
        meta = {
            "actor": actor_user_id,
            "resource": resource,
            "result": result,
            "request_id": request_id,
            **(metadata or {}),
        }
        with psycopg.connect(
            get_settings().database_url,
            connect_timeout=max(1, int(get_settings().database_timeout_seconds)),
        ) as conn:
            conn.execute(
                "INSERT INTO audit_logs "
                "(entity_type, action, actor_user_id, occurred_at, metadata, "
                "resource, result, request_id) "
                "VALUES (%s, %s, %s, now(), %s::jsonb, %s, %s, %s)",
                (
                    "account",
                    action,
                    actor_user_id,
                    json.dumps(meta),
                    resource,
                    result,
                    request_id,
                ),
            )
            conn.commit()
    except Exception:
        pass


ANONYMIZATION_ACTION = "USER_ACCOUNT_ANONYMIZED"
ANONYMIZATION_REASON = "LGPD_USER_REQUEST"


def _anonymization_audit(user_id: str, request_id: str, result: str, **extra: object):
    """Statement and parameters for the anonymization audit row.

    The metadata is built from a fixed set of keys on purpose: nothing taken from the
    user's record (e-mail, name, portfolio names, notes) and no raw exception text, which
    database drivers may fill with the offending value.
    """
    metadata = {
        "reason": ANONYMIZATION_REASON,
        "result": result,
        "request_id": request_id,
        **extra,
    }
    statement = (
        "INSERT INTO audit_logs (entity_type, entity_id, action, actor_user_id, "
        "occurred_at, metadata, resource, result, request_id) "
        "VALUES ('user', %s, %s, %s, now(), %s::jsonb, 'account', %s, %s)"
    )
    params = (
        user_id,
        ANONYMIZATION_ACTION,
        user_id,
        json.dumps(metadata),
        result,
        request_id,
    )
    return statement, params


@router.get(
    "/account/data-export",
    tags=["account"],
)
def export_user_data(
    request: Request,
    current_user: AuthUserResponse = Depends(get_current_user),
) -> dict:
    req_id = request_id_for(request)
    settings = get_settings()

    try:
        with psycopg.connect(settings.database_url) as conn:
            # 1. Profile
            user_row = conn.execute(
                "SELECT id, email, status, created_at FROM users WHERE id = %s",
                (current_user.id,),
            ).fetchone()

            if not user_row:
                raise HTTPException(status_code=404, detail="User profile not found")

            profile = {
                "id": str(user_row[0]),
                "email": str(user_row[1]),
                "status": str(user_row[2]),
                "created_at": user_row[3].isoformat() if user_row[3] else None,
            }

            # 2. Watchlists and Items
            watchlist_rows = conn.execute(
                "SELECT w.id, w.name, wi.id, wi.instrument_id, i.canonical_id "
                "FROM watchlists w "
                "LEFT JOIN watchlist_items wi ON wi.watchlist_id = w.id "
                "LEFT JOIN instruments i ON wi.instrument_id = i.id "
                "WHERE w.user_id = %s",
                (current_user.id,),
            ).fetchall()

            watchlists_dict = {}
            for row in watchlist_rows:
                w_id = str(row[0])
                w_name = str(row[1])
                item_id = str(row[2]) if row[2] else None
                instrument_id = str(row[3]) if row[3] else None
                canonical_id = str(row[4]) if row[4] else None

                if w_id not in watchlists_dict:
                    watchlists_dict[w_id] = {
                        "id": w_id,
                        "name": w_name,
                        "items": [],
                    }
                if item_id:
                    watchlists_dict[w_id]["items"].append(
                        {
                            "id": item_id,
                            "instrument_id": instrument_id,
                            "canonical_id": canonical_id,
                        }
                    )

            # 3. Portfolios
            portfolio_rows = conn.execute(
                "SELECT id, name, base_currency, created_at, archived_at "
                "FROM portfolios "
                "WHERE user_id = %s",
                (current_user.id,),
            ).fetchall()

            portfolios = []
            for row in portfolio_rows:
                portfolios.append(
                    {
                        "id": str(row[0]),
                        "name": str(row[1]),
                        "base_currency": str(row[2]),
                        "created_at": row[3].isoformat() if row[3] else None,
                        "archived_at": row[4].isoformat() if row[4] else None,
                    }
                )

            # 4. Ledger (Portfolio Events)
            ledger_rows = conn.execute(
                "SELECT pe.id, pe.portfolio_id, pe.event_type, pe.event_date, "
                "pe.instrument_id, i.canonical_id, pe.quantity, pe.price, "
                "pe.gross_amount, pe.fees, pe.cash_amount, pe.currency, pe.created_at, "
                "pe.note "
                "FROM portfolio_events pe "
                "LEFT JOIN instruments i ON pe.instrument_id = i.id "
                "WHERE pe.created_by = %s",
                (current_user.id,),
            ).fetchall()

            ledger = []
            for row in ledger_rows:
                ledger.append(
                    {
                        "id": str(row[0]),
                        "portfolio_id": str(row[1]),
                        "event_type": str(row[2]),
                        "event_date": row[3].isoformat() if row[3] else None,
                        "instrument_id": str(row[4]) if row[4] else None,
                        "canonical_id": str(row[5]) if row[5] else None,
                        # Decimal strings, never float: money and quantities keep precision.
                        "quantity": str(row[6]) if row[6] is not None else None,
                        "price": str(row[7]) if row[7] is not None else None,
                        "gross_amount": str(row[8]) if row[8] is not None else None,
                        "fees": str(row[9]) if row[9] is not None else None,
                        "cash_amount": str(row[10]) if row[10] is not None else None,
                        "currency": str(row[11]),
                        "created_at": row[12].isoformat() if row[12] else None,
                        "note": str(row[13]) if row[13] is not None else None,
                    }
                )

        # Audit Log
        _record_account_audit(
            actor_user_id=current_user.id,
            action="data_export",
            resource="account",
            result="success",
            request_id=req_id,
        )

        return {
            "profile": profile,
            "watchlists": list(watchlists_dict.values()),
            "portfolios": portfolios,
            "ledger": ledger,
        }
    except Exception as exc:
        _record_account_audit(
            actor_user_id=current_user.id,
            action="data_export",
            resource="account",
            result="failed",
            request_id=req_id,
            metadata={"error_type": type(exc).__name__},
        )
        raise HTTPException(status_code=500, detail="Data export failed")


@router.delete(
    "/account",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["account"],
)
def delete_user_account(
    request: Request,
    response: Response,
    current_user: AuthUserResponse = Depends(get_current_user),
) -> Response:
    req_id = request_id_for(request)
    settings = get_settings()
    cookie_name = settings.auth_cookie_name
    auth = get_auth_service()
    marker_written = False
    committed = False

    try:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                # 1. Anonymize user personal data and set status to DELETED
                # Preserves referential integrity for tables like portfolio_events and audit_logs
                dummy_email = f"deleted-{current_user.id}@market-pulse.invalid"
                dummy_hash = f"deleted_placeholder_{uuid4()}"

                cur.execute(
                    "UPDATE users SET email = %s, password_hash = %s, status = 'DELETED', "
                    "updated_at = now() WHERE id = %s",
                    (dummy_email, dummy_hash, current_user.id),
                )

                # 2. Sessions live only in Redis (revoked below); the legacy "sessions" table
                # is unused by any code, so nothing is deleted from it.

                # 3. Clean up watchlists and watchlist items (non-audit critical)
                cur.execute(
                    "DELETE FROM watchlist_items WHERE watchlist_id IN "
                    "(SELECT id FROM watchlists WHERE user_id = %s)",
                    (current_user.id,),
                )
                cur.execute(
                    "DELETE FROM watchlists WHERE user_id = %s",
                    (current_user.id,),
                )

                # 4. Archive the portfolios and neutralize their free-text name. The ledger
                # (portfolio_events) stays bound to user_id; id, user_id, base_currency and
                # dates do not change.
                cur.execute(
                    "UPDATE portfolios SET archived_at = now(), "
                    "name = 'Carteira removida ' || id::text WHERE user_id = %s",
                    (current_user.id,),
                )

                # 4b. Erase the ledger's free-text notes (ADR-010). The append-only trigger
                # accepts exactly this change - note to NULL, nothing else - and refuses any
                # other UPDATE or DELETE, so amounts, dates and ids stay intact.
                cur.execute(
                    "UPDATE portfolio_events SET note = NULL WHERE note IS NOT NULL "
                    "AND portfolio_id IN (SELECT id FROM portfolios WHERE user_id = %s)",
                    (current_user.id,),
                )

                # 5. Revoke every session in Redis BEFORE the commit, so an unreachable
                # Redis rolls the whole anonymization back instead of leaving other devices
                # logged in. The marker is flagged first: revoke_user writes it before it
                # does anything else that can fail.
                marker_written = True
                sessions_revoked = auth.revoke_user(current_user.id)

                # 6. Audit row in the same transaction: no anonymization without a record.
                statement, params = _anonymization_audit(
                    current_user.id, req_id, "success", sessions_revoked=sessions_revoked
                )
                cur.execute(statement, params)

            conn.commit()
            committed = True

        # Expire/delete the cookie in the response headers
        response_obj = Response(status_code=status.HTTP_204_NO_CONTENT)
        response_obj.delete_cookie(cookie_name, path="/")
        return response_obj

    except Exception as exc:
        # A failure before the commit means the account was NOT anonymized, so the user
        # must not stay locked out for the whole session TTL by a marker we wrote.
        if marker_written and not committed:
            try:
                auth.restore_user(current_user.id)
            except Exception:
                pass
        try:
            statement, params = _anonymization_audit(
                current_user.id, req_id, "failed", error_type=type(exc).__name__
            )
            with psycopg.connect(settings.database_url) as audit_conn:
                audit_conn.execute(statement, params)
                audit_conn.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Account deletion failed")
