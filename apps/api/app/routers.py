import hashlib
import json
import secrets

import psycopg
from fastapi import APIRouter, Cookie, Header, HTTPException, Query, Request, Response, status

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
    PortfolioEventAccepted,
    PortfolioEventCreate,
    PublicHistorySeries,
    PublicQuote,
    RegisterRequest,
    SeriesMode,
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

router = APIRouter(prefix="/api/v1")


def get_auth_service() -> AuthService:
    return AuthService()


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


@router.get("/watchlists", tags=["watchlists"])
def list_watchlists() -> dict[str, list]:
    return {"items": []}


@router.get("/portfolios", tags=["portfolios"])
def list_portfolios() -> dict[str, list]:
    return {"items": []}


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
