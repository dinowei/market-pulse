import hashlib
import json
import secrets

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

from app.auth.service import (
    AuthConflict,
    AuthInvalid,
    AuthRateLimited,
    AuthService,
    AuthUnavailable,
)
from app.contracts import (
    AuthUserResponse,
    HistoryPeriod,
    InstrumentList,
    InstrumentSummary,
    LoginRequest,
    PageMeta,
    PortfolioCashBalanceResponse,
    PortfolioCreateRequest,
    PortfolioEventAccepted,
    PortfolioEventCreate,
    PortfolioEventRequest,
    PortfolioEventResponse,
    PortfolioListResponse,
    PortfolioPatchRequest,
    PortfolioPositionResponse,
    PortfolioResponse,
    PortfolioSummaryResponse,
    PublicHistorySeries,
    PublicQuote,
    RegisterRequest,
    SeriesMode,
    WatchlistCreateRequest,
    WatchlistItemCreateRequest,
    WatchlistItemResponse,
    WatchlistListResponse,
    WatchlistPatchRequest,
    WatchlistReorderRequest,
    WatchlistResponse,
)
from app.core.config import get_settings
from app.errors import request_id as request_id_for
from app.instruments.catalog import (
    CatalogStatus,
    CoverageTier,
    DataSupportStatus,
    search_catalog,
)
from app.market_data.normalization import AdjustmentType
from app.market_data.public_market_data import public_history, public_quote
from app.market_data.refresh_application import (
    RefreshBatchRequest,
    RefreshBatchResponse,
    refresh_market_data,
)
from app.portfolios.service import (
    PortfolioConflict,
    PortfolioNotFound,
    PortfolioService,
    PortfolioValidationError,
    PostgresPortfolioService,
)
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
    service = get_auth_service()
    cookie_name = get_settings().auth_cookie_name
    if cookie_name != "market_pulse_session":
        session_token = request.cookies.get(cookie_name)
    try:
        return service.me(session_token)
    except (AuthInvalid, AuthUnavailable) as exc:
        raise _auth_error(request, exc) from exc


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
) -> PublicHistorySeries:
    try:
        return public_history(
            canonical_id,
            period,
            mode,
            request_id_for(request),
            adjustment_type.value,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Instrument not found") from exc


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


@router.post(
    "/portfolio-events",
    response_model=PortfolioEventAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["portfolio-events"],
)
def create_portfolio_event(
    payload: PortfolioEventCreate,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PortfolioEventAccepted:
    if not idempotency_key or len(idempotency_key) > 128:
        raise HTTPException(status_code=422, detail="Idempotency-Key header is required")
    body_hash = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn:
        row = conn.execute(
            "SELECT body_hash, response_json FROM idempotency_keys "
            "WHERE key=%s AND method=%s AND path=%s",
            (idempotency_key, request.method, request.url.path),
        ).fetchone()
        if row:
            if row[0] != body_hash:
                raise HTTPException(
                    status_code=409, detail="Idempotency-Key was reused with a different payload"
                )
            stored_response = row[1] if isinstance(row[1], dict) else json.loads(row[1])
            return PortfolioEventAccepted.model_validate(stored_response)
        response = PortfolioEventAccepted(idempotency_key=idempotency_key)
        conn.execute(
            "INSERT INTO idempotency_keys (key, method, path, body_hash, "
            "response_json) VALUES (%s,%s,%s,%s,%s)",
            (
                idempotency_key,
                request.method,
                request.url.path,
                body_hash,
                response.model_dump_json(),
            ),
        )
        conn.commit()
    return response


@router.get("/performance", tags=["performance"])
def performance() -> dict[str, list]:
    return {"items": []}


@router.get("/morning-call", tags=["morning-call"])
def morning_call() -> dict[str, list]:
    return {"items": []}


@router.get("/editorial", tags=["editorial"])
def editorial() -> dict[str, list]:
    return {"items": []}
