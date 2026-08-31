from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(title="Market Pulse API", version="0.1.0")


@app.get("/health", tags=["diagnostics"])
def health() -> dict[str, str]:
    """Return a non-sensitive process diagnostic."""
    return {
        "status": "ok",
        "version": app.version,
        "environment": "local",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
