# Cache and Freshness Day 12 Implementation Plan

> **For agentic workers:** Execute task-by-task with TDD and fresh verification at each gate.

**Goal:** Add a Redis-compatible cache-aside layer, deterministic market freshness engine, stale-if-error, negative caching, granular invalidation and owned distributed locks without changing public routes.

**Architecture:** Keep PostgreSQL/provider provenance authoritative and place a small backend protocol in `app.market_data.cache`. A Redis adapter and deterministic in-memory backend share the same interface; cache envelopes retain provenance, DataLevel, Freshness and expiry metadata. A separate freshness module uses explicit IANA timezone and a weekday market calendar, avoiding provider calls and frontend/OpenAPI changes.

**Tech Stack:** Python 3.11+, `redis` 6.4, Decimal, zoneinfo, pytest, Ruff, PostgreSQL/Redis Compose.

**Spec:** Dia 12 prompt; `docs/ARCHITECTURE.md`, `docs/market_data/NORMALIZATION_DAY_10.md`, `docs/policies/FINANCIAL_DATA_AND_PORTFOLIO_INTEGRITY_POLICY.md` and existing provider contracts.

## Global Constraints

- Cache never upgrades `DataLevel`, hides `STALE`, removes provenance or makes `DEMO` look real.
- Redis is an optimization; PostgreSQL/provider provenance remain authoritative.
- No real provider, key, data, scraping, Stripe, broker, push, deploy, login or global `FLUSHALL`.
- Negative cache distinguishes `NOT_FOUND`, `OUT_OF_SCOPE`, `DATA_UNAVAILABLE` and `LICENSE_BLOCKED`.
- Locks require TTL, unique owner and owner-only release.

### Task 1: Write failing freshness and cache contract tests

**Files:** Create `apps/api/tests/test_cache_freshness_day12.py`.

- [x] Cover granular key construction, cache miss/hit provenance, DataLevel preservation, EOD/DEMO semantics, timezone/DST, stale-if-error, negative-cache expiry, granular invalidation, lock ownership and secret-free keys/log-safe errors.
- [x] Run the focused test file and confirm failure because `app.market_data.cache` and `app.market_data.freshness` do not exist.

### Task 2: Implement deterministic freshness engine

**Files:** Create `apps/api/app/market_data/freshness.py`.

- [x] Define `FreshnessResult`, explicit TTL policy by DataLevel, weekday calendar and timezone-aware `compute_freshness`.
- [x] Return `UNAVAILABLE` for missing/future timestamps, safe `STALE` for DEMO, and never promote EOD/DELAYED to REAL_TIME.
- [x] Run freshness-focused tests until green.

### Task 3: Implement cache backend and cache-aside service

**Files:** Create `apps/api/app/market_data/cache.py`.

- [x] Define key builders, cache envelope serialization preserving Decimal/provenance, Redis and in-memory backends, cache-aside loader flow and stale-if-error fallback.
- [x] Add negative caching with short TTL, granular invalidation and safe failure handling when Redis is unavailable.
- [x] Add owned distributed lock with TTL and compare-and-delete release.
- [x] Run focused tests and existing API tests.

### Task 4: Document and validate

**Files:** Create `docs/market_data/CACHE_FRESHNESS_DAY_12.md`; update `docs/AGENTS.md` with the canonical link.

- [x] Document keys, TTLs, calendar/freshness semantics, stale-if-error, negative cache, invalidation and locks, including Redis/database failure behavior and the display contract.
- [x] Preserve OpenAPI and generated client because no public route changes.
- [x] Run migrations/tests/Ruff, web lint/typecheck/test/build, secret scan, diff check and Compose shutdown.
