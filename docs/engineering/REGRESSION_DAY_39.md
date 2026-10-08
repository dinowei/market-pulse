# Regressão completa e hardening (Dia 39)

- **Data:** 2026-10-07 (UTC).
- **Branch:** `feature/dia-31-34`, sem deploy.
- **Escopo do roadmap:** regressão de backend, frontend, E2E, testes financeiros, temas,
  tokens, gráficos e heatmap, "nas rodadas oficiais e no CI", mais os itens do Dia 39
  decididos em 2026-10-05: H-23, Redis persistente e plano Vercel.

## 1. Matriz de regressão

| Verificação | Comando | Resultado |
| --- | --- | --- |
| Backend completo | `uv run python -m pytest -q` | **407 passed**, 10 skipped (opt-in), 0 failed |
| Lint do backend (comando do CI) | `ruff check app tests` | Limpo |
| Formatação do backend | `ruff format --check app tests` | 6 arquivos dos Dias 25 a 27 fora do padrão (H-18, preexistente) |
| Contrato | OpenAPI gerado × `docs/api/openapi.json`; `npm run generate:api` | Sincronizados |
| Frontend: lint, typecheck e testes | `npm run lint`, `tsc --noEmit`, `npm test` | Limpos; **80 testes** |
| Build de produção | `npm run build` | OK (11 rotas do app, mais as páginas de erro) |
| Desempenho e bundle | `node scripts/day27_performance_gate.mjs` | Passa: fixtures, medições reais do staging e orçamento de bundle |
| E2E de acessibilidade | `day36-wcag.spec.ts` e `day27-a11y.spec.ts` | **29 de 29** (11 rotas × 2 temas, reflow, teclado, movimento reduzido e smoke do Dia 27) |
| E2E principal com DEMO (`demo.spec.ts`) | — | **Não executado:** exige Postgres e Redis locais (Docker parado) ou CI |
| Rodadas oficiais (`release-gate.yml`) | — | **Não executadas:** GitHub Actions bloqueado pela cobrança (H-05) |

Os E2E rodaram localmente, com a API sem DEMO e sem banco: rotas privadas sem sessão e o
Morning Call em carregamento. Os estados com sessão e com DEMO ficam para o CI ou o
Docker.

## 2. Defeitos encontrados e corrigidos neste dia

| # | Defeito | Origem | Correção | Prova |
| --- | --- | --- | --- | --- |
| Q-1 | A tabela equivalente da comparação pareava valores **pela posição** e não pela data: mostrava o IBOV de outubro na linha de 08/09 | Dia 26 | Linhas alinhadas por instante (`comparisonRows`); célula vazia onde a série não tem ponto | `apps/web/app/day39-frontend.test.ts`; conferido no navegador |
| Q-2 | A escala vertical da comparação se ajusta às séries sem aviso: 0,002 ponto parecia uma alta forte | Dia 26 | A legenda declara o intervalo do eixo ("de 100 a 100,002") | Mesmo teste |
| H-22 | `/compare` usava um id fixo que não existe no catálogo DEMO e abria em erro | Dia 26 | Ativo padrão escolhido do catálogo servido (`GET /instruments`); benchmark Ibovespa | Mesmo teste |
| H-24 | Cliente Redis novo a cada `AuthService` | Dia 18 | Um cliente por processo e configuração (`app/core/redis_client.py`) | `test_shared_redis_day39.py` |
| H-25 D-5 | `archived_at` recebia o horário da publicação | Dia 23 | Horário do arquivamento; publicação preservada | `test_editorial_archive_time_day39.py` |

## 3. H-23: mecanismo pronto, ativação pendente

A [ADR-020](../adr/020-trusted-proxy-hops.md) implementa o IP do cliente por saltos de
proxy confiáveis, com testes de forja. O padrão continua 0 (o comportamento atual),
porque há dois caminhos até a API (pela Vercel e direto no Render), e N só é seguro com
uma cadeia única e medida. A medição e o fechamento do caminho direto exigem deploy.

## 4. Itens do Dia 39 que dependem do usuário

| Item | Por que depende | Referência |
| --- | --- | --- |
| Redis persistente (R1 ou R3) | Contratação | H-03 e H-04 no [handoff](../DAY29_HANDOFF.md) |
| Plano Vercel adequado a uso não pessoal | Contratação; o Hobby é só para uso pessoal | H-07 |
| Plano da API sem hibernação | Contratação; cold start de 52,8 s | H-27 |
| CI e rodadas oficiais | Desbloquear a cobrança do GitHub | H-05 |
| Levar os Dias 30 a 39 ao staging | Autorização de deploy (o push em `feature/dia-29-staging` vai para a produção da Vercel) | CLAUDE.md |
| Assinatura de compliance do Morning Call | Revisão humana | H-13 |
| D-1 e D-3 do fluxo editorial | Decisão em ADR | H-25 |
| Revisão de acessibilidade com leitor de tela e zoom | Revisão humana | [Dia 36](../design/ACCESSIBILITY_DAY_36.md) |

## 5. Estado do gate

A regressão automatizada local passou e os defeitos encontrados foram corrigidos com
teste. O gate do Dia 39 **não fecha** sem as rodadas oficiais em CI e o E2E com DEMO, que
dependem do H-05 ou do Docker local.
