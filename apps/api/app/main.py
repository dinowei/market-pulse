from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.health import check_cache, check_database, timestamp

settings = get_settings()
app = FastAPI(title="Market Pulse API", version=settings.api_version)


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
