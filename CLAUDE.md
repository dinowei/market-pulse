# Market Pulse

@AGENTS.md

As instruções operacionais completas estão em `AGENTS.md`, importado acima, e as
regras complementares de documentação em [docs/CLAUDE.md](docs/CLAUDE.md).

## Estado atual

Somente fatos verificados. Não promova hipótese a decisão nesta seção.

- **Dias 24 a 27: fechados.** Demonstração local persistida e isolada, painel
  operacional interno, comparação multiativo, calendário econômico, proventos,
  marcadores e telemetria Web Vitals.
- **Dia 28: PARCIAL (não fechado).** Implementado e commitado localmente na branch
  `feature/dia-28-hardening`; a branch está à frente do remoto.
  - **Medido** (Claude Code, 2026-10-01, Neon `dev` + Upstash): suíte de backend com
    338 passed, 1 failed (`test_demo_browser_day24`, depende de Redis local), 10
    skipped (opt-in, exigem banco local). Expurgo real validado em Postgres
    descartável. Números observados, não meta.
  - **Informado, não conferido:** validação local E1–E13 (usuário), causa do bloqueio
    do GitHub, cota do Upstash.
  - **Falta:** Rodada 1 (`run_local.ps1`), Rodada 2 (`run_frontend.ps1`), push
    autorizado, resolução do CI (`startup_failure`, sem evidência automatizada), ADR
    da opção B e as pendências de [DAY29_HANDOFF.md](docs/DAY29_HANDOFF.md)
    (artefatos de deploy, CSP, `sessions`, cadastro aberto etc.).

- **Decisões de 2026-10-01 (decididas pelo usuário):** exclusão de conta =
  anonimização com D1–D5; artefatos de deploy (Dockerfile non-root, shutdown
  gracioso) saem do Dia 28 e vão para o Dia 29 ([DAY29_HANDOFF.md](docs/DAY29_HANDOFF.md)).
- **Dívida de lint preexistente:** 82 erros em `migrations/` e 23 arquivos fora do
  `ruff format` (handoff H-18); `app` e `tests` passam no `ruff check` do CI.

## Retomada: próximo passo exato

1. **Rodada 1:** reiniciar o PC, abrir só o Docker Desktop e rodar
   `powershell -ExecutionPolicy Bypass -File C:\Projetos\mp-local-checkun_local.ps1`.
2. **Rodada 2:** reiniciar sem abrir o Docker e rodar o `run_frontend.ps1` da mesma pasta.
3. Analisar 429/403/5xx do E2E **sem relaxar rate limit nem CSRF**.
4. Push só com autorização explícita.
5. Declarar o Dia 28 fechado **somente** com as duas rodadas verdes e a evidência
   registrada. Se uma janela dos scripts for fechada à força, renomear
   `appspi\.env.mp-local-check-hold` de volta para `.env`.

Detalhes em [PRODUCTION_RUNBOOK_DAY_28.md](docs/operations/PRODUCTION_RUNBOOK_DAY_28.md).
