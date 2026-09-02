# Dia 12.1 — Reconciliacao, invariantes e refresh interno — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconciliar as fontes canônicas com a execução real, reforçar identidade/provenance/default deny e criar refresh interno idempotente sem provider real.

**Architecture:** Uma camada de decisão de acesso será aplicada antes de provider, cache, fallback e refresh. A identidade canônica persistirá em migration incremental; dados de mercado usarão provenance mínima; refresh será um serviço interno síncrono, sem rota pública, apoiado por lock, ingestion run, DemoProvider e persistência em memória/test doubles até existir fluxo de banco autorizado.

**Tech Stack:** FastAPI/Python 3.11+, Pydantic, PostgreSQL/Alembic, Redis-compatible cache/lock, Decimal, pytest, Ruff, OpenAPI gerado.

**Spec:** Prompt do Dia 12.1, `docs/PROJECT_SPEC.md`, `docs/ARCHITECTURE.md`, políticas financeiras, baseline enterprise e ADRs 005–007.

## Global Constraints

- Não editar migrations históricas; toda alteração de schema será migration incremental.
- Não ativar provider real, chave, dado real, scraping, Stripe, corretora, push, deploy ou login externo.
- Não criar frontend visual neste dia e não transformar stubs em dados aparentes.
- Licenciamento é default deny por provider, plano, endpoint/capability, dataset, finalidade, modalidade e ambiente.
- `DataLevel` e `Freshness` permanecem separados; `DEMO` nunca parece dado real.
- Valores financeiros usam `Decimal`/`NUMERIC`; timestamps financeiros são timezone-aware.
- `portfolio_events` permanece append-only e Morning Call permanece não prescritivo.

---

### Task 1: Reconciliar roadmap e arquitetura

**Files:**
- Modify: `docs/ROADMAP_30_DAYS.md`
- Modify: `docs/ARCHITECTURE.md`
- Create: `docs/engineering/DAY_12_1_RECONCILIATION_AND_REFRESH.md`

- [x] Atualizar as tabelas para refletir Dias 8–12 reais e mover a antiga tarefa de API para Dia 13/12.2.
- [x] Registrar causas, compatibilidade e limites, sem apagar histórico.
- [x] Documentar refresh interno, status, lock, audit trail e o que fica para Dia 13.

### Task 2: Guardrails estruturais (TDD)

**Files:**
- Modify: `apps/api/app/contracts.py`
- Modify: `apps/api/app/providers/models.py`
- Modify: `apps/api/app/providers/licensing.py`
- Modify: `apps/api/app/providers/gateway.py`
- Modify: `apps/api/app/market_data/normalization.py`
- Modify: `apps/api/app/providers/normalization.py`
- Test: `apps/api/tests/test_day12_1_guardrails.py`

- [x] Escrever testes falhando para enum canônico, moeda/timestamp obrigatórios, decisão multidimensional, cache sem licença e adapter sem payload bruto.
- [x] Implementar `THIRD_PARTY_CONSENSUS` no contrato novo e compatibilidade legada somente na borda de leitura.
- [x] Criar `DatasetAccessRequest`/`DatasetAccessDecision` com provider, plano, capability, dataset, finalidade, modalidade, ambiente, review status e DataLevel permitido.
- [x] Aplicar decisão no gateway e expor uma função reutilizável para refresh/cache.
- [x] Remover default USD e exigir currency em normalização externa; validar invariantes OHLC e timestamp.

### Task 3: Migration incremental de identidade e provenance

**Files:**
- Create: `apps/api/migrations/versions/20260902_0005_identity_provenance.py`
- Modify: `apps/api/tests/test_schema.py`
- Test: `apps/api/tests/test_day12_1_schema.py`

- [x] Escrever testes de presença/unique/index de `instruments.canonical_id` e provenance em quotes, bars e FX.
- [x] Adicionar migration compatível que preencha canonical IDs determinísticos para linhas existentes antes de `NOT NULL`.
- [x] Adicionar dataset/status/freshness/source/timestamps/ingestion/raw references onde faltarem; manter `NUMERIC`/`TIMESTAMPTZ`.
- [x] Testar upgrade/downgrade/upgrade sem editar migrations anteriores.

### Task 4: Adapter boundary e refresh idempotente

**Files:**
- Modify: `apps/api/app/providers/candidate_adapters.py`
- Create: `apps/api/app/market_data/refresh.py`
- Modify: `apps/api/app/market_data/cache.py`
- Test: `apps/api/tests/test_refresh_day12_1.py`

- [x] Escrever testes para `SKIPPED_LICENSE_BLOCKED`, `SKIPPED_LOCKED`, `SUCCESS`, `PARTIAL`, `FAILED` e `UNAVAILABLE`.
- [x] Fazer adapters exigirem normalizador injetado e retornarem `ProviderResult`, mantendo raw payload apenas sanitizado.
- [x] Implementar serviço `RefreshService` sem rota pública: decisão de licença, lock, `ingestion_run`, DemoProvider opcional como DEMO, normalização, idempotência, invalidação granular e liberação owner-only.
- [x] Criar persistência/test double determinístico e não chamar provider quando não aprovado.

### Task 5: Validação e documentação final

**Files:**
- Modify: `docs/AGENTS.md` (somente se novo documento canônico exigir link)
- Modify: `docs/market_data/CACHE_FRESHNESS_DAY_12.md` (somente se contrato mudar)

- [x] Rodar migrations, API tests, Ruff, web lint/typecheck/test/build, secret scan e diff check.
- [x] Validar OpenAPI/cliente se contratos públicos mudarem; manter stubs sem dados reais.
- [x] Subir/derrubar Compose local e confirmar working tree limpa.
- [x] Revisar diff por código fora do escopo, segredos e ausência de provider real.
