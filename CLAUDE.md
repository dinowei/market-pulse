# Market Pulse

@AGENTS.md

As instruções operacionais completas estão em `AGENTS.md`, importado acima, e as
regras complementares de documentação em [docs/CLAUDE.md](docs/CLAUDE.md).

## Estado atual

Somente fatos verificados. Não promova hipótese a decisão nesta seção.

- **Dias 24 a 27: fechados.** Demonstração local persistida e isolada, painel
  operacional interno, comparação multiativo, calendário econômico, proventos,
  marcadores e telemetria Web Vitals.
- **Dia 28: PARTIAL.** Implementado e commitado na branch
  `feature/dia-28-hardening`, validado fora do CI, com pendências abertas.
  - Suíte de backend na nuvem (Neon + Upstash), conferida em 2026-10-01:
    **329 passed, 1 failed, 10 skipped**. A falha é `test_demo_browser_day24`,
    que depende de Redis em `localhost`; os 10 skips são testes opt-in de banco
    local.
  - Validação local E1–E13: informada como OK pelo responsável pelo produto; o
    log não foi conferido por Claude Code.
  - O CI do repositório está em `startup_failure`, condição anterior a esta
    branch, portanto **não há evidência automatizada**.
  - Expurgo (`python -m app.cli.retention`): executado de verdade em Postgres real
    descartável (14 de 14 verificações); falta só o dry-run no DEMO local.
  - **Ainda não rodaram:** o teste ponta a ponta da anonimização de conta em banco
    local e o E2E do frontend (Playwright). Não existe nenhum Dockerfile; o
    roadmap pede artefatos non-root para o Dia 28 (runbook, seção 5.14).
  - Decisão de 2026-10-01 (usuário): exclusão de conta = anonimização +
    desativação. Risco residual: `portfolio_events.note`; a ADR da opção B é
    obrigatória antes de abrir o produto a outros usuários.

O Dia 28 só pode ser declarado concluído depois de fechadas as pendências e
registrada a evidência. Como rodar na nuvem e localmente, decisões e pendências
em [PRODUCTION_RUNBOOK_DAY_28.md](docs/operations/PRODUCTION_RUNBOOK_DAY_28.md).
