# Dia 13 — Internal Refresh Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expor o refresh de mercado somente por endpoint interno autenticado por segredo, com limites, lock, idempotência e falhas parciais controladas.

**Architecture:** A rota FastAPI valida `X-Cron-Secret` com `secrets.compare_digest` e delega a um serviço de aplicação independente de FastAPI. O serviço reutiliza licensing, `RefreshService`, lock e cache existentes; nenhuma sessão de usuário ou provider real autoriza a operação.

**Tech Stack:** FastAPI, Pydantic strict, Python 3.11+, secrets, pytest, PostgreSQL/Alembic, Redis-compatible cache.

**Spec:** Prompt do Dia 13 em `docs/PROJECT_SPEC.md` e instruções operacionais do prompt aprovado.

## Global Constraints

- Endpoint interno não é endpoint de usuário e falha fechado sem segredo.
- Comparação do segredo usa `secrets.compare_digest`; nunca registrar o valor recebido.
- Não ativar provider real, chave, dado real, scraping, Stripe, corretora, push, deploy ou login externo.
- DemoProvider permanece `DataLevel.DEMO`; Default Deny continua valendo para provider, dataset, cache e fallback.
- Valores financeiros usam Decimal/NUMERIC; payloads externos não atravessam a fronteira do domínio.

### Task 1: RED tests for secure internal refresh

**Files:**
- Create: `apps/api/tests/test_internal_refresh_day13.py`
- Modify: `apps/api/tests/test_health.py` only if shared app fixtures require it

- [x] Write tests for absent/wrong/correct `X-Cron-Secret`, user cookie/Bearer rejection, strict payload, batch limits, empty list, run ID, lock, idempotency and partial failures.
- [x] Run the focused tests and confirm failure because the route/service/configuration is missing.

### Task 2: Configuration and application service

**Files:**
- Modify: `apps/api/app/core/config.py`
- Modify: `apps/api/app/market_data/refresh.py`
- Create: `apps/api/app/market_data/refresh_application.py`

- [x] Add typed optional secret and strict batch/time limits with safe local defaults.
- [x] Implement `refresh_market_data` as framework-independent orchestration returning sanitized run summaries and per-item failures.
- [x] Ensure license denial happens before provider invocation, locks are owner-only, and cache invalidation is granular.

### Task 3: Protected internal route

**Files:**
- Modify: `apps/api/app/routers.py`
- Modify: `apps/api/app/errors.py` only if existing Problem Details mapping cannot represent safe 401/413/503 responses
- Modify: `apps/api/app/main.py` only if dependency wiring is required
- Modify: `apps/api/tests/test_openapi_snapshot.py` if the versioned internal route changes the contract

- [x] Add strict request/response models and `POST /api/v1/internal/refresh-quotes`.
- [x] Require only `X-Cron-Secret`, use the existing request ID, reject cookies/Bearer-only auth, and avoid exposing internals.
- [x] Keep the route out of frontend usage and regenerate the contract client because the versioned route is in OpenAPI.

### Task 4: Documentation and environment example

**Files:**
- Modify: `.env.example`
- Create: `docs/market_data/REFRESH_DAY_13.md`
- Create: `docs/operations/INTERNAL_REFRESH_ENDPOINT.md`
- Modify: `docs/ROADMAP_30_DAYS.md` only if Day 13 wording is stale

- [x] Document header, fail-closed behavior, limits, run IDs, locks, idempotency, partial failures, cache invalidation and future cron usage.
- [x] Use only `local_demo_only_change_me` or an empty value as the example secret.

### Task 5: Validation and commits

- [x] Run migration gate, API tests, Ruff, web checks, OpenAPI synchronization check, secret scan, diff check and Compose teardown.
- [x] Review staged diff for scope, provider activation and secret leakage.
- [x] Commit tests, implementation and docs separately with Conventional Commits.
