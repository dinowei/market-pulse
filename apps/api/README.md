# Market Pulse API

Foundation-only FastAPI application for Day 3. `/health/live` checks process
liveness and `/health/ready` checks local PostgreSQL and Redis. Providers,
authentication, persistence models and financial domain logic remain outside
this scaffold.

Run from the repository root:

```powershell
python -m uv sync --project apps/api --group dev
docker compose up -d postgres redis
python -m uv run --directory apps/api uvicorn app.main:app --reload
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
docker compose down
```

The local Compose credentials are demonstrative only. Production Redis may use
an approved REST adapter later; no Upstash or other external service is used by
this application today.
