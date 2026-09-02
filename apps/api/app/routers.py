import hashlib
import json
import secrets

import psycopg
from fastapi import APIRouter, Header, HTTPException, Query, Request, status

from app.contracts import InstrumentList, PageMeta, PortfolioEventAccepted, PortfolioEventCreate
from app.core.config import get_settings
from app.errors import request_id as request_id_for
from app.market_data.refresh_application import (
    RefreshBatchRequest,
    RefreshBatchResponse,
    refresh_market_data,
)

router = APIRouter(prefix="/api/v1")


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
    return InstrumentList(items=[], meta=PageMeta(limit=limit, offset=offset, next_offset=None))


@router.get("/market-data/quotes/latest", tags=["market-data"])
def latest_quote() -> dict[str, list]:
    return {"items": []}


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
