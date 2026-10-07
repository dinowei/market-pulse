# Market Pulse — dossiê do release candidate (Dia 30)

- **Data:** 2026-10-05
- **Branch:** `feature/dia-30-rc`, sobre `feature/dia-29-staging`
- **Classificação:** **RC do staging privado com P0 incompleto** (decisão do usuário,
  seção "Fase 2" do [roadmap](../ROADMAP_30_DAYS.md)). Não é release de produção nem
  abertura do produto.
- **Estado do gate:** **ABERTO.** Este dossiê reúne a evidência existente; o gate só
  fecha quando os itens marcados como PENDENTE tiverem prova.

Origem da evidência: **MEDIDO** = executado por Claude Code nesta data, com saída vista;
**INFORMADO** = executado e informado pelo responsável; **PENDENTE** = sem prova.

## 1. Escopo do Dia 30 entregue

| Item | Estado | Referência |
|---|---|---|
| H-08, notas do ledger anuladas na anonimização | Implementado | [ADR-010](../adr/010-portfolio-event-note-erasure.md), migration `20261005_0012` |
| H-09, CSRF antes do rate limit e cabeçalhos em toda resposta | Implementado | [ADR-009](../adr/009-csrf-before-rate-limit.md) |
| H-11, decisão sobre convite | Decidido; implementação antes da abertura | [ADR-011](../adr/011-registration-by-invite.md) |
| H-17, teste dependente de Redis local | Resolvido como efeito da ADR-009 | [DAY29_HANDOFF.md](../DAY29_HANDOFF.md) |

## 2. Regressão

| Verificação | Resultado | Origem |
|---|---|---|
| Suíte de backend (Neon `market_pulse_test` + Upstash de teste), 2026-10-06 | 369 passed, 10 skipped (opt-in), **0 failed** | MEDIDO |
| Smoke do staging privado (Dia 29) | health, docs fechados, cadastro fechado, proxy e CSRF pela mesma origem, shutdown gracioso e zero 5xx. Login e sessão pendentes | MEDIDO ([runbook](../operations/STAGING_RUNBOOK_DAY_29.md), §7) |
| H-17 isolado, código do Dia 29 x Dia 30 | falha x passa, sem Redis local | MEDIDO |
| Frontend: 37 testes unitários, lint, typecheck, build com proxy | OK no código do Dia 29; o Dia 30 não altera `apps/web` | MEDIDO |
| Ruff no escopo do CI (`app`, `tests`) | OK | MEDIDO |
| 10 testes opt-in (DEMO, migration populada, ciclo de conta) | Rodada 1 | PENDENTE |
| E2E (a11y, principal, isolamento) | Rodada 2 | PENDENTE |
| CI no GitHub Actions | `startup_failure` desde antes do Dia 28 (H-05) | PENDENTE |

## 3. Migrations e rollback

| Verificação | Resultado | Origem |
|---|---|---|
| `20261005_0012`: upgrade, downgrade e upgrade no Postgres de teste | OK; revisão final `20261005_0012 (head)` | MEDIDO |
| Regra da trigger num banco real | anulação aceita; 5 alterações recusadas (valor, reescrita da nota, nota com outra coluna, `NULL` para `NULL`, `DELETE`); verificação desfeita por rollback | MEDIDO |
| Rollback de schema | `alembic downgrade -1`; notas anuladas não voltam (por design, ADR-010) | MEDIDO |

## 4. Segurança e privacidade

| Controle | Estado |
|---|---|
| Cookie de sessão `HttpOnly`, `Secure` fora de local/test, `SameSite` só `lax`/`strict` em staging/produção | Código e testes |
| CSRF por Origin, antes do rate limit, independente do Redis | ADR-009 |
| Cabeçalhos de segurança em 2xx, 403, 429 e 503 | ADR-009 |
| `/docs`, `/redoc` e `/openapi.json` fechados em staging/produção | Dia 29 |
| Cadastro fechado por padrão em staging/produção | Dia 29; convite: ADR-011 |
| Anonimização sem texto livre residual no ledger | ADR-010 |
| Segredos fora do repositório; Blueprint sem valores sensíveis (`render.yaml`) | Revisão de diff a cada commit |
| IP real atrás de proxy (H-23) | Forja medida e **mitigada** no staging ([ADR-012](../adr/012-untrusted-proxy-headers.md)); a solução definitiva continua obrigatória antes da abertura (Dia 39) |

## 5. Licenças, dados e limitações

- Nenhum provider tem `PUBLIC_APPROVED` na [matriz de licenças](../DATA_PROVIDER_LICENSE_MATRIX.md);
  todos estão `UNREVIEWED` e bloqueados. O staging roda sem DEMO e sem provider, e deve
  exibir `UNAVAILABLE` explícito (H-12).
- **P0 incompleto:** Global Atlas tabular e heatmap básico nunca foram entregues;
  agendados para o Dia 37.
- **Infraestrutura grátis:**
  - a API dorme após 15 min sem tráfego e volta em cerca de 1 min;
  - o Postgres do staging expira 30 dias após a criação e não tem backup;
  - o Key Value não tem persistência;
  - o Vercel Hobby é só para uso pessoal e não comercial (H-07).
- O repositório `dinowei/market-pulse` é **público**: toda a documentação e a
  infraestrutura como código ficam visíveis. Nenhum segredo é versionado.

## 6. Pendências para fechar o gate do Dia 30

1. **Rodadas oficiais na nuvem (decisão do usuário, 2026-10-07):** as etapas de
   `run_local.ps1` (E2–E13) e `run_frontend.ps1` (F1–F9) foram convertidas no workflow
   `.github/workflows/release-gate.yml`. Ele roda a cada push e PR. As regras são as das
   rodadas: etapa opt-in com skip reprova; o E2E roda em 3 execuções espaçadas; qualquer
   403, 429 ou 5xx reprova. A sintaxe dos 16 scripts e a lógica de análise dos logs foram
   validadas localmente. **Bloqueio:** a conta GitHub está travada por cobrança (H-05), e só
   o usuário resolve isso em `github.com/settings/billing`. Depois disso, o workflow vira a
   evidência oficial e substitui as rodadas manuais. Os scripts locais ficam como reserva.
2. **Usuário:** criar a conta única do staging (runbook, §6) para o smoke de login e
   sessão. Depois, levar o código do Dia 30 ao staging. Ele inclui a migration `0012`,
   que roda no boot. Deploys de produção ficam com o usuário, porque o modo de
   permissões bloqueia o agente.
3. **Usuário:** resolver a cobrança do GitHub Actions (H-05) e obter um `ci.yml` verde.
4. Depois de 1 a 3: tag do RC, decisão de versionamento e fechamento deste dossiê.
