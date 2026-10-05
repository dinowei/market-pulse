# Market Pulse

@AGENTS.md

As instruções operacionais completas estão em `AGENTS.md`, importado acima, e as
regras complementares de documentação em [docs/CLAUDE.md](docs/CLAUDE.md).

## Estado atual

Somente fatos verificados. Não promova hipótese a decisão nesta seção.

- **Dias 24 a 27: fechados.** Demonstração local persistida e isolada, painel
  operacional interno, comparação multiativo, calendário econômico, proventos,
  marcadores e telemetria Web Vitals.
- **Dia 28: FECHADO em 2026-10-01**, por decisão do usuário, na branch
  `feature/dia-28-hardening`. Evidências por origem (as rodadas locais foram
  **executadas e informadas pelo responsável**, logs fora do repositório):
  - **Medido** (Claude Code, Neon `dev` + Upstash): suíte de backend com 341 passed,
    1 failed (`test_demo_browser_day24`, depende de Redis local), 10 skipped
    (opt-in); frontend com 33 testes unitários passed; expurgo real validado em
    Postgres descartável. Números observados, não meta.
  - **Rodada 1** (`run_local.ps1`, 21:11): E1–E13 OK, negativo com 10 skipped, 11
    testes opt-in passed, retenção dry-run OK.
  - **Rodada 2** (`run_frontend.ps1`, 22:02): build OK, E2E 6 passed (a11y 4,
    principal 1, isolation 1), nenhum 403/429/5xx. Achados corrigidos pelo E2E:
    contraste em `/portfolios` e balde de rate limit próprio para a telemetria.
    A repetição das 22:59 identificou o 12º 404 (`/compare`, H-22) e registrou
    queda do Docker por RAM (evento de ambiente).
  - **Sem prova automatizada:** CI em `startup_failure` (anterior à branch).
- **Decisões de 2026-10-01 (decididas pelo usuário):** exclusão de conta =
  anonimização com D1–D5 (ADR da opção B obrigatória antes de abrir o produto);
  artefatos de deploy (Dockerfile non-root, shutdown gracioso) saem do Dia 28 e vão
  para o Dia 29.
- **Dívida conhecida:** lint/formatação preexistente (H-18) e demais pendências em
  [DAY29_HANDOFF.md](docs/DAY29_HANDOFF.md).
- **Dia 29: EM ANDAMENTO** na branch local `feature/dia-29-staging` (sem push).
  - **Escopo:** reconciliado como preparação e deploy de staging **privado** (adendo no roadmap).
  - **Feito em 2026-10-05**, por decisões técnicas delegadas pelo usuário:
    - cadastro fechado por padrão em staging/produção;
    - `/docs`, `/redoc` e `/openapi.json` fechados em staging/produção;
    - `SameSite=none` recusado no boot;
    - proxy same-origin no Next.js ([ADR-008](docs/adr/008-same-origin-api-proxy.md));
    - [runbook do staging](docs/operations/STAGING_RUNBOOK_DAY_29.md).
  - **Medido** (Claude Code): backend com 356 passed, 1 failed (o mesmo H-17), 10 skipped; frontend com 37 testes unitários, lint, typecheck e build OK.
  - **Falta:** rodadas oficiais no PowerShell, push autorizado, contas e painéis (usuário) e o smoke do staging.

## Ferramentas (decisão do usuário, a partir do Dia 29)

Claude Desktop (aba Code) é a ferramenta principal e o VS Code é a reserva; **nunca
os dois abertos juntos** (a máquina tem 3,7 GB de RAM). Rodadas oficiais de validação
só no PowerShell, com os scripts de `C:\Projetos\mp-local-check`.

## Próximo passo

Concluir o Dia 29:

1. O usuário roda as rodadas oficiais na branch `feature/dia-29-staging`.
2. O usuário autoriza o push.
3. O usuário cria contas e recursos e segue o
   [runbook do staging](docs/operations/STAGING_RUNBOOK_DAY_29.md).
4. O smoke do staging é registrado.

O GitHub Actions agendado continua bloqueado (H-05, decisão C4). Pendências em
[DAY29_HANDOFF.md](docs/DAY29_HANDOFF.md). Push, deploy, login externo e merge na `main`
exigem autorização específica. Detalhes do Dia 28 em
[PRODUCTION_RUNBOOK_DAY_28.md](docs/operations/PRODUCTION_RUNBOOK_DAY_28.md).
