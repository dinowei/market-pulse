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
- **Dia 29: STAGING NO AR desde 2026-10-06; gate ainda aberto.**
  - **Endereços:** web `https://market-pulse-staging.vercel.app` (projeto Vercel
    `market-pulse`, produção na branch `feature/dia-29-staging`) e API
    `https://market-pulse-staging-api.onrender.com` (Blueprint `market-pulse-staging`).
  - **Smoke medido**, registrado no runbook §7: health, docs fechados, cadastro fechado,
    proxy e CSRF pela mesma origem, shutdown gracioso e zero 5xx.
  - **Smoke completo em 2026-10-07:** conta única criada pelo usuário; login, sessão pelo
    proxy (watchlist 200/201) e logout 204 medidos nos logs; cadastro fechado de novo
    (404). O 422 do cadastro foi corrigido no formulário (`60df9ca`).
  - **Falta para fechar o gate:** as rodadas oficiais, as mesmas do Dia 30.
  - O PR [dinowei/market-pulse#1](https://github.com/dinowei/market-pulse/pull/1) foi
    aberto pelo usuário e **não deve receber merge** antes das rodadas e do CI verde.
  - **Mudança de deploy:** um push em `feature/dia-29-staging` agora implanta a produção
    da Vercel.
  - **Escopo:** reconciliado como preparação e deploy de staging **privado** (adendo no roadmap).
  - **Feito em 2026-10-05**, por decisões técnicas delegadas pelo usuário:
    - cadastro fechado por padrão em staging/produção;
    - `/docs`, `/redoc` e `/openapi.json` fechados em staging/produção;
    - `SameSite=none` recusado no boot;
    - proxy same-origin no Next.js ([ADR-008](docs/adr/008-same-origin-api-proxy.md));
    - [runbook do staging](docs/operations/STAGING_RUNBOOK_DAY_29.md).
  - **Medido** (Claude Code): backend com 356 passed, 1 failed (o mesmo H-17), 10 skipped; frontend com 37 testes unitários, lint, typecheck e build OK.
  - **Medido em 2026-10-06:** forja de IP pelo `X-Forwarded-For` no Render, mitigada
    pela [ADR-012](docs/adr/012-untrusted-proxy-headers.md); CORS aceita JSON ou lista
    separada por vírgula.
- **Dia 30: GATE ABERTO** na branch `feature/dia-30-rc` ([dossiê do RC](docs/engineering/DAY_30_RELEASE_CANDIDATE.md)).
  - **Feito em 2026-10-05:**
    - H-08 ([ADR-010](docs/adr/010-portfolio-event-note-erasure.md), migration `20261005_0012`);
    - H-09 ([ADR-009](docs/adr/009-csrf-before-rate-limit.md));
    - decisão de convite ([ADR-011](docs/adr/011-registration-by-invite.md));
    - H-17 resolvido como efeito da ADR-009;
    - `render.yaml` (Blueprint do staging).
  - **Medido:**
    - backend em 2026-10-06 com 369 passed, 10 skipped, 0 failed;
    - migration 0012 aplicada, revertida e reaplicada no Postgres de teste;
    - a limitação do provider DEMO deixou de dizer "local".
  - **Falta:**
    - rodadas oficiais;
    - smoke de login e sessão no staging;
    - CI verde (H-05);
    - levar o código do Dia 30 ao staging (H-08, H-09 e migration 0012 ainda não estão lá).
- **Dias 31–34: entregues em 2026-10-07** na branch `feature/dia-31-34` (sem deploy),
  por autorização do usuário com o gate do Dia 30 aberto. Estado e evidência na seção
  "Fase 2" do [roadmap](docs/ROADMAP_30_DAYS.md):
  - downsampling M4 (ADR-013);
  - SVG P0 mantido (ADR-014);
  - tokens OKLCH e contraste AA nos dois temas (ADR-015).

  Faltam a validação em CI (H-05) e a revisão visual humana.
- **Plano de 40 dias (decisão do usuário, 2026-10-05):**
  - **Fase 2 (Dias 31–40):** registrada como **planejada** na seção "Fase 2" do
    [roadmap](docs/ROADMAP_30_DAYS.md). Só começa após o Dia 30 fechado, e cada dia
    exige autorização.
  - **Lacunas verificadas e decididas pelo usuário:**
    - o Global Atlas tabular e o heatmap básico (ambos P0, nunca entregues) vão
      para o Dia 37, e o RC do Dia 30 é "RC do staging privado com P0 incompleto";
    - os itens antes de abrir o produto ficam distribuídos: Dia 30 (H-08, H-09,
      convite), Dia 35 (H-13, H-19, H-21) e Dia 39 (H-23, Redis persistente, plano
      Vercel).

## Ferramentas (decisão do usuário, a partir do Dia 29)

Claude Desktop (aba Code) é a ferramenta principal e o VS Code é a reserva; **nunca
os dois abertos juntos** (a máquina tem 3,7 GB de RAM).

**Rodadas oficiais (decisão do usuário, 2026-10-07):** passam a ser o workflow
`.github/workflows/release-gate.yml` no GitHub Actions, equivalente a `run_local.ps1` +
`run_frontend.ps1`. Ele depende de desbloquear a cobrança da conta GitHub (H-05). Os
scripts de `C:\Projetos\mp-local-check` (PowerShell, PC reiniciado, só o Docker aberto)
ficam como reserva.

## Próximo passo

Concluir o Dia 29:

1. O usuário roda as rodadas oficiais na branch `feature/dia-29-staging`.
2. O usuário cria contas e recursos e segue o
   [runbook do staging](docs/operations/STAGING_RUNBOOK_DAY_29.md).
3. O smoke do staging é registrado.

O GitHub Actions agendado continua bloqueado (H-05, decisão C4). Pendências em
[DAY29_HANDOFF.md](docs/DAY29_HANDOFF.md). Push, deploy, login externo e merge na `main`
exigem autorização específica. Detalhes do Dia 28 em
[PRODUCTION_RUNBOOK_DAY_28.md](docs/operations/PRODUCTION_RUNBOOK_DAY_28.md).
