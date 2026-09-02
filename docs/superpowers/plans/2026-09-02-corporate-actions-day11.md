# Corporate Actions Day 11 Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with TDD and verify each gate before proceeding.

**Goal:** Add a deterministic, append-only corporate-actions ingestion and reconciliation foundation for dividends, JCP, splits and reverse splits without activating real providers or applying wallet credits.

**Architecture:** Extend the existing modular `apps/api/app/market_data` domain with typed Decimal normalization and an in-memory reconciliation store suitable for deterministic tests. Add a reversible Alembic migration that preserves the existing `corporate_actions` table identity while adding controlled status, external idempotency, provenance, raw-payload and correction links. Keep portfolio ledger untouched and document the boundary between event ingestion and future portfolio application.

**Tech Stack:** Python 3.11+, Pydantic, Decimal, pytest, Ruff, SQLAlchemy/Alembic, PostgreSQL.

**Spec:** Attached Dia 11 prompt; canonical references `docs/market_data/NORMALIZATION_DAY_10.md`, `docs/policies/FINANCIAL_DATA_AND_PORTFOLIO_INTEGRITY_POLICY.md`, ADR-007 and `docs/ROADMAP_30_DAYS.md`.

## Global Constraints

- No real provider call, key, real financial data, scraping, Stripe, login, push or deploy.
- `PUBLIC_APPROVED` is not granted; DemoProvider fixtures remain synthetic and `DEMO`.
- Never mutate or delete `portfolio_events`; wallet crediting is deferred to the later portfolio/performance days.
- Monetary values and ratios use `Decimal`/PostgreSQL `NUMERIC`; never `float`.
- Invalid or incomplete events are quarantined or marked `UNAVAILABLE`; missing fields are never inferred.

### Task 1: Define failing normalization and reconciliation tests

**Files:** Create `apps/api/tests/test_corporate_actions_day11.py`.

- [ ] Add tests for valid CASH_DIVIDEND, JCP, SPLIT and REVERSE_SPLIT Decimal normalization.
- [ ] Add tests for missing currency/ex-date, non-positive amount/ratio, duplicate external keys, correction history, cancellation retention, conflicts, sanitized payloads, default deny, DemoProvider `DEMO`, portfolio immutability and batch isolation.
- [ ] Run `Push-Location apps/api; $env:PYTHONPATH='.'; python -m uv run pytest -q tests/test_corporate_actions_day11.py` and confirm the expected missing-module failures.

### Task 2: Implement the minimal corporate-action domain

**Files:** Create `apps/api/app/market_data/corporate_actions.py`; modify `apps/api/app/providers/demo.py` only if required.

- [ ] Define exact enums `CorporateActionType` (`CASH_DIVIDEND`, `JCP`, `SPLIT`, `REVERSE_SPLIT`) and `CorporateActionStatus` (`PENDING`, `CONFIRMED`, `CORRECTED`, `CANCELLED`, `UNAVAILABLE`).
- [ ] Normalize dates, Decimal amount/ratio and provenance without accepting floats; validate type-specific required fields.
- [ ] Implement deterministic external key generation and an append-only in-memory reconciler with duplicate no-op, correction versioning, cancellation retention, conflict quarantine and per-item batch isolation.
- [ ] Expose a projection helper for future split quantity/value equivalence without writing `portfolio_events`.
- [ ] Run the focused tests until green, then the existing API unit suite.

### Task 3: Extend DemoProvider safely

**Files:** Modify `apps/api/app/providers/demo.py`; modify `apps/api/tests/test_market_adapters.py` only if the new contract needs an explicit assertion.

- [ ] Return synthetic, clearly marked `DEMO` corporate-action payloads for dividend/JCP/split paths; do not add network transport or real data.
- [ ] Keep provider licensing default-deny and run focused provider tests.

### Task 4: Add reversible PostgreSQL schema support

**Files:** Create `apps/api/migrations/versions/20260902_0004_corporate_actions_pipeline.py`; modify `apps/api/tests/test_schema.py` only for new structural assertions.

- [ ] Add status, announced/ex/record/payment/effective dates, external key fields, version/correction links, ingestion/raw-payload links and controlled amount/ratio constraints to `corporate_actions`.
- [ ] Add a unique idempotency index scoped by provider/dataset/instrument/action/external key and preserve prior versions.
- [ ] Add a dedicated quarantine table for incomplete/conflicting actions; do not alter `portfolio_events`.
- [ ] Verify upgrade, downgrade and upgrade again against local PostgreSQL.

### Task 5: Document the pipeline and verify all gates

**Files:** Create `docs/market_data/CORPORATE_ACTIONS_DAY_11.md`.

- [ ] Document event types, fields, statuses, dates, idempotency, versioning, correction/cancellation, quarantine, wallet boundary and Decimal rules.
- [ ] Run API migration/tests/Ruff, web lint/typecheck/test/build, OpenAPI snapshot checks, `git diff --check`, secret scan and Docker shutdown.
- [ ] Review the complete diff for real data, secrets, provider activation or unintended portfolio changes.
