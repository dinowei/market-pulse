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

O Dia 28 só pode ser declarado concluído depois que as rodadas locais rodarem
verdes e a evidência for registrada. Detalhes em
[PRODUCTION_RUNBOOK_DAY_28.md](docs/operations/PRODUCTION_RUNBOOK_DAY_28.md).
