from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.errors import (
    http_exception_handler,
    problem,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.health import check_cache, check_database, timestamp
from app.middleware import RequestIdMiddleware
from app.routers import router

settings = get_settings()
app = FastAPI(title="Market Pulse API", version=settings.api_version)
if settings.demo_enabled:
    from app.demo.operations import demo_settings

    demo_settings()  # fail startup closed if any dedicated-local barrier is missing
    demo_origins = ("http://localhost:3000",)

    @app.middleware("http")
    async def demo_origin_guard(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin not in {None, *demo_origins}:
            return problem(request, 403, "Forbidden", "Origin not allowed", "FORBIDDEN")
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(demo_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
app.add_middleware(RequestIdMiddleware)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.include_router(router)


@app.get("/health", tags=["diagnostics"])
def health() -> dict[str, str]:
    """Return a non-sensitive process diagnostic."""
    return {
        "status": "ok",
        "version": app.version,
        "environment": settings.environment,
        "timestamp": timestamp(),
    }


@app.get("/health/live", tags=["diagnostics"])
def health_live() -> dict[str, str]:
    return {"status": "ok", "timestamp": timestamp()}


@app.get("/health/ready", tags=["diagnostics"])
async def health_ready() -> JSONResponse:
    checks: dict[str, str] = {}
    for name, checker in (("database", check_database), ("cache", check_cache)):
        try:
            checks[name] = "ok" if await checker(settings) else "failed"
        except Exception:
            checks[name] = "failed"

    ready = all(value == "ok" for value in checks.values())
    body = {"status": "ok" if ready else "not_ready", "checks": checks, "timestamp": timestamp()}
    return JSONResponse(body, status_code=200 if ready else status.HTTP_503_SERVICE_UNAVAILABLE)
