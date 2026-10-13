# Market Pulse: handoff final da Fase 2 (Dia 40)

- **Data:** 2026-10-07 (UTC).
- **Fonte de verdade das pendências:** [DAY29_HANDOFF.md](DAY29_HANDOFF.md) (itens H-01 a
  H-27). Este documento resume o estado e a ordem das próximas ações; não substitui as
  ADRs nem os relatórios.
- **Por onde começar:** este documento; depois o [índice de ADRs](adr/README.md), o
  [checklist de compliance](COMPLIANCE_CHECKLIST.md) e o
  [runbook de promoção](operations/STAGING_PROMOTION_DAYS_30_40.md).

## 1. Onde está cada coisa

| Branch | Conteúdo | Situação |
| --- | --- | --- |
| `main` | Primeiro commit | Intocada. O PR [dinowei/market-pulse#1](https://github.com/dinowei/market-pulse/pull/1) **não deve receber merge** antes do CI verde e das rodadas oficiais |
| `feature/dia-29-staging` | Dia 29 (staging privado) | **Implantada:** um push nela atualiza a produção da Vercel; o Render acompanha o Blueprint |
| `feature/dia-30-rc` | Dia 30 (RC do staging privado com P0 incompleto) | Contém a de cima; sem deploy |
| `feature/dia-31-34` | Dias 31 a 40 (o nome ficou do início da fase) | Contém as duas de cima; sem deploy |

Ambiente no ar: web `https://market-pulse-staging.vercel.app` e API
`https://market-pulse-staging-api.onrender.com`, ambos com o **código do Dia 29**.

## 2. Estado dos gates

| Dia | Entrega | Gate | O que falta |
| --- | --- | --- | --- |
| 29 | Staging privado, smoke completo | Aberto | Rodadas oficiais (H-05) |
| 30 | H-08, H-09, decisão de convite, `render.yaml` | Aberto | Rodadas oficiais; deploy no staging |
| 31 | Downsampling M4 ([ADR-013](adr/013-history-display-downsampling.md)) | Evidência local | CI |
| 32 | SVG mantido ([ADR-014](adr/014-chart-engine-keep-svg.md)) | Evidência local | CI |
| 33–34 | Tokens OKLCH e contraste AA ([ADR-015](adr/015-oklch-tokens-and-theme-contrast.md)); tema global ([ADR-016](adr/016-global-persisted-theme.md)) | Evidência local | CI; revisão visual de Cláudio |
| 35 | H-19 ([ADR-017](adr/017-per-user-rate-limit.md)), H-21 ([ADR-018](adr/018-portfolio-overview-and-aligned-downsampling.md)), avisos do §11 | Evidência local | **Assinatura de compliance (H-13)** |
| 36 | WCAG 2.2 AA e daltonismo ([relatório](design/ACCESSIBILITY_DAY_36.md)) | Parte automática aprovada | Leitor de tela e zoom (revisão humana); varredura com sessão |
| 37 | Global Atlas tabular e heatmap básico ([ADR-019](adr/019-global-atlas-table-and-basic-heatmap.md)) | Evidência local | Dados reais exigem dataset `PUBLIC_APPROVED` |
| 38 | Web Vitals no staging real e bundle ([relatório](engineering/PERFORMANCE_DAY_38.md)) | Medido, dentro dos budgets | Medir os Dias 30–40 após o deploy |
| 39 | Regressão e hardening ([relatório](engineering/REGRESSION_DAY_39.md)); H-23 ([ADR-020](adr/020-trusted-proxy-hops.md)) | Aberto | CI, E2E com DEMO e contratações |
| 40 | README, [design system](design/DESIGN_SYSTEM.md), [alternativas descartadas](engineering/DISCARDED_ALTERNATIVES.md) e este handoff | Fechado | — |

**Última medição local** (2026-10-07): backend com 407 passed, 10 skipped e 0 failed;
frontend com 80 testes, lint, typecheck e build OK; gate de desempenho OK; E2E de
acessibilidade com 29 de 29.

## 3. Próximas ações, em ordem

Cada item depende do usuário: contratação, autorização ou revisão humana.

1. **Desbloquear a cobrança do GitHub** (H-05). Isso libera o CI e o `release-gate.yml`,
   que substitui as rodadas manuais, e o E2E com DEMO.
2. **Autorizar o deploy dos Dias 30 a 40 no staging.** Como o push em
   `feature/dia-29-staging` implanta a produção da Vercel, a ação exige autorização
   explícita. O passo a passo, o smoke e o rollback estão no
   [runbook de promoção](operations/STAGING_PROMOTION_DAYS_30_40.md). Depois dele,
   repetir a medição do Dia 38 e medir a cadeia de proxies (H-23).
3. **Assinar a revisão de compliance do Morning Call** (H-13,
   [pacote](editorial/MORNING_CALL_COMPLIANCE_REVIEW.md)) e decidir D-1 e D-3 do fluxo
   editorial em ADR (H-25).
4. **Decidir os planos:** Redis persistente (H-03 e H-04), Vercel para uso não pessoal
   (H-07) e API sem hibernação (H-27, cold start medido de 52,8 s).
5. **Revisão humana de acessibilidade:** leitor de tela e zoom de 200%.

## 4. Obrigatório antes de abrir o produto a outras pessoas

| Item | Estado |
| --- | --- |
| Cadastro por convite ([ADR-011](adr/011-registration-by-invite.md)) | Decidido, **não implementado**: exige migration e consumo transacional verificados em Postgres |
| IP real atrás de proxies (H-23) | Mecanismo pronto e desligado; falta medir e fechar o acesso direto ao Render |
| Compliance do Morning Call (H-13, H-25) | Pacote pronto; falta assinatura e ADR do fluxo |
| Planos pagos (H-03, H-07, H-27) | Decisão do usuário |
| CI verde e rodadas oficiais (H-05) | Bloqueado pela cobrança |
| Dívida de formatação (H-18) | 6 arquivos dos Dias 25 a 27 fora do `ruff format` |

## 5. Notas de suporte

| Sintoma | Causa conhecida | O que fazer |
| --- | --- | --- |
| Primeira carga sem dados por quase 1 min | API hibernada no plano grátis do Render (52,8 s medidos) | Esperar; a solução é o plano (H-27) |
| Muitas variações "indisponíveis" no staging | DEMO desligado: as cotações sintéticas não têm fechamento anterior | Esperado; dados reais exigem dataset `PUBLIC_APPROVED` |
| 429 para vários anônimos ao mesmo tempo | Sem IP real, todos chegam como `127.0.0.1` e dividem o balde | Esperado até ativar a ADR-020; usuários com sessão têm balde próprio (ADR-017) |
| Cadastro responde 404 | Cadastro fechado em staging por desenho | Abrir só com `MARKET_PULSE_REGISTRATION_ENABLED=true` e fechar em seguida |
| E2E local preso em "Carregando" | Postgres e Redis locais parados (Docker) | Ver o relatório do [Dia 36](design/ACCESSIBILITY_DAY_36.md), §3 |

## 6. Problemas conhecidos

| Problema | Impacto | Item |
| --- | --- | --- |
| CI e rodadas oficiais sem execução | Nenhum gate dos Dias 29 a 39 tem prova em CI | H-05 |
| Aviso de privacidade e termos de uso inexistentes | Bloqueia abrir o produto a terceiros | [Checklist](COMPLIANCE_CHECKLIST.md), §3 |
| CSP do frontend ausente | Defesa em profundidade incompleta no navegador | H-02 |
| Telemetria só com médias | Sem P95 de campo | H-26 |
| Margem de LCP móvel estreita em `/portfolios` e `/calendar` | 87% a 90% do budget | [Dia 38](engineering/PERFORMANCE_DAY_38.md), P-2 |
| Formatação pendente em 6 arquivos antigos | Ruído no `ruff format --check` | H-18 |

## 7. Como verificar o estado

```bash
cd apps/api && uv run python -m pytest -q
```

```bash
cd apps/web && npm run lint && npm run typecheck && npm test && npm run build
```

```bash
node scripts/day27_performance_gate.mjs
```

O E2E de acessibilidade (`apps/web/e2e/day36-wcag.spec.ts`) exige a web em
`localhost:3000` e a API em `localhost:8000`.
