# Promoção dos Dias 30 a 40 para o staging

- **Data:** 2026-10-07 (Dia 40). **Ainda não executado.**
- **Base:** [runbook do staging](STAGING_RUNBOOK_DAY_29.md); este documento acrescenta
  só o que muda com os Dias 30 a 40.
- **Este documento não autoriza deploy.** Push na branch do staging implanta a produção da
  Vercel e exige autorização explícita do usuário.

## 1. Pré-requisitos

1. Cobrança do GitHub desbloqueada (H-05).
2. `release-gate.yml` verde em `feature/dia-31-34`: backend, frontend e E2E.
3. Autorização explícita do usuário para este deploy.

## 2. O que muda no ambiente

| Mudança | Efeito no deploy | Referência |
| --- | --- | --- |
| Migration `20261005_0012` | Aplicada pelo `alembic upgrade head` do comando de start | [ADR-010](../adr/010-portfolio-event-note-erasure.md) |
| Ordem dos middlewares | CSRF passa a ser avaliado antes do rate limit | [ADR-009](../adr/009-csrf-before-rate-limit.md) |
| Chaves de rate limit com prefixo `ip:` ou `user:` | Os contadores recomeçam do zero uma vez | [ADR-017](../adr/017-per-user-rate-limit.md) |
| Nova variável `MARKET_PULSE_TRUSTED_PROXY_HOPS` | Declarada com `0` no `render.yaml`; o padrão já é 0, então nada muda sem ela | [ADR-020](../adr/020-trusted-proxy-hops.md) |
| Rotas novas na API | `GET /instruments` com o catálogo, `GET /market-data/heatmap` e `GET /portfolios/{id}/overview` | ADR-018 e ADR-019 |
| Rotas novas na web | `/atlas` e `/heatmap` | ADR-019 |

## 3. Passos

1. Confirmar que a promoção é um avanço rápido, sem reescrever histórico:

   ```bash
   git merge-base --is-ancestor origin/feature/dia-29-staging origin/feature/dia-31-34
   ```

2. Promover sem `--force` (o Git recusa se não for avanço rápido):

   ```bash
   git push origin feature/dia-31-34:feature/dia-29-staging
   ```

3. **Render:** o serviço implanta a cada commit (`autoDeployTrigger: commit`). No Dia 29,
   uma mudança de comando de start só valeu depois do **Manual sync** do Blueprint; repetir
   o sync para aplicar o `render.yaml` novo.
4. **Vercel:** a produção implanta a partir da mesma branch.
5. Acompanhar os logs do Render até o `alembic` registrar a revisão `20261005_0012` e o
   health responder.

## 4. Smoke

Executar o §7 do [runbook do staging](STAGING_RUNBOOK_DAY_29.md) e acrescentar:

| Verificação | Esperado |
| --- | --- |
| `GET /api/v1/instruments` | Catálogo com região, bolsa e fuso |
| `GET /api/v1/market-data/heatmap` | Grupos por tipo de instrumento e limitações declaradas |
| `/compare` | Abre com o ativo do catálogo e o Ibovespa; tabela alinhada por data |
| `/atlas` e `/heatmap` | Renderizam com o aviso legal |
| `/portfolios`, com sessão | Uma requisição `/overview` por carteira |
| Dashboard | Variação com direção, sinal e palavra, ou "Variação indisponível" |
| Respostas 5xx nos logs | Nenhuma |

Depois do smoke:

- repetir a medição do Dia 38 (`apps/web/performance/measure-vitals.mjs`) nos perfis
  desktop e móvel;
- registrar o resultado em `apps/web/performance/day38-staging.json` e rodar o gate.

## 5. Rollback

- **Código:** §8 do runbook do staging (reimplantar o deployment anterior, commit
  `60df9ca`, pelo painel de cada plataforma).
- **Schema:** `alembic downgrade -1` reverte a 0012 (medido no Postgres de teste, [dossiê
  do Dia 30](../engineering/DAY_30_RELEASE_CANDIDATE.md) §3). Notas anuladas não voltam,
  por desenho.
- **Código antigo com a 0012 aplicada:** por análise de código, e sem medição, a
  migration só passa a aceitar a anulação da nota, operação que o código do Dia 29 nunca
  executa. Por isso, o rollback de código não exigiria o de schema. Confirmar antes de
  depender disso.

## 6. Limitações que continuam depois da promoção

- DEMO desligado no staging (`MARKET_PULSE_DEMO_ENABLED=false`): as cotações são
  sintéticas, rotuladas `DEMO`, e a maioria das variações aparece como indisponível.
- Cadastro fechado e convite não implementado (ADR-011).
- IP real desligado (ADR-020): anônimos e login seguem num balde único por IP.
- Cold start de cerca de 53 s no plano grátis do Render (H-27).
