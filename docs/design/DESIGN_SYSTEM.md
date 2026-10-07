# Design system Particle Atlas: referência do que está implementado

- **Data:** 2026-10-07 (Dia 40).
- **Natureza:** inventário do código em `apps/web` na branch `feature/dia-31-34`. A norma
  continua sendo a [diretriz Particle Atlas](PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md) e a
  [semântica de gráficos](PARTICLE_ATLAS_CHART_SEMANTICS.md); em conflito, elas
  prevalecem e este documento deve ser corrigido.
- **Decisões que o moldaram:** [ADR-005](../adr/005-hybrid-progressive-rendering.md),
  [ADR-006](../adr/006-monochrome-financial-chart-semantics.md),
  [ADR-014](../adr/014-chart-engine-keep-svg.md),
  [ADR-015](../adr/015-oklch-tokens-and-theme-contrast.md),
  [ADR-016](../adr/016-global-persisted-theme.md) e
  [ADR-019](../adr/019-global-atlas-table-and-basic-heatmap.md).

## 1. Tokens

Definidos em `apps/web/app/globals.css`, com o mesmo valor em hex e em `oklch()`
(dentro de `@supports`). O tema vale para todas as páginas em `<html data-theme>`.

| Token | Escuro | Claro | Uso |
| --- | --- | --- | --- |
| `--pa-bg-canvas` | `#08090a` | `#f3f5f7` | Fundo da página |
| `--pa-bg-surface` | `#111317` | `#ffffff` | Painéis |
| `--pa-bg-elevated` | `#171a20` | `#e9edf1` | Elevação (blocos do heatmap, resultados de busca) |
| `--pa-border-hairline` | `#2a2e35` | `#c3c9d1` | Grades e divisórias |
| `--pa-border-control` | `#636870` | `#81868e` | Borda de campos (≥ 3:1) |
| `--pa-text-primary` | `#f7f7f5` | `#111317` | Texto e linha financeira principal |
| `--pa-text-secondary` | `#a7adb6` | `#4f5966` | Metadados |
| `--pa-accent-neutral` | `#a7adb6` | `#4f5966` | Ponto da série principal; marca de `FRESH` |
| `--pa-market-up` | `#5ee68a` | `#137a3c` | Direção `UP` |
| `--pa-market-down` | `#ff7272` | `#b42323` | Direção `DOWN` |
| `--pa-market-flat` | `#72b7ff` | `#075da8` | Direção `FLAT`, benchmark e links |
| `--pa-state-stale` | `#ffad5c` | `#9a5100` | Só `STALE` e alerta restrito |
| `--pa-state-unavailable` | `#8b929d` | `#5c6570` | `UNAVAILABLE` |
| `--pa-state-demo` | `#e3e7ed` | `#303942` | `DEMO` |
| `--pa-focus` | `#ffffff` | `#111317` | Contorno de foco |

**Contraste (testado):** texto ≥ 4,5:1 e foco e bordas de controle ≥ 3:1 nos dois temas
(`oklch-tokens-day33.test.ts`, `day35-frontend.test.ts`, `day36-a11y.test.ts`). O menor
valor das cores de direção é 4,60:1 (alta, tema claro, fundo elevado).

### Tipografia, forma e camadas

Também extraídos de `globals.css`. O que não existe está dito como inexistente, em vez de
uma escala sugerida.

| Aspecto | Implementado |
| --- | --- |
| Família | `Arial, Helvetica, sans-serif` no corpo; `monospace` só para ids de requisição no painel interno |
| Pesos | 400 e 700 |
| Títulos | `h1`: `clamp(1.5rem, 3vw, 2.5rem)`, altura de linha 1,1; `h2`: `1rem` |
| Texto auxiliar | Entre `.66rem` e `.85rem`; os mais usados são `.68rem`, `.72rem` e `.75rem` |
| Altura de linha | 1,1 (títulos), 1,45 e 1,5 (texto corrido) |
| Espaçamento | **Sem escala formal**: valores em `rem` por componente; o mais comum é `1rem`, e as páginas usam `clamp(1rem, 4vw, 3rem)` de margem interna |
| Raio | Um token, `--pa-radius: 4px`; `999px` no selo de estado e `50%` na marca do selo |
| Sombra | **Nenhuma**: profundidade por fundo (`canvas`, `surface`, `elevated`) e borda |
| Breakpoints | `max-width: 1050px` e `max-width: 700px` |
| Camadas | Um único `z-index: 2`, nos resultados da busca |

**Estados de interação:**

| Estado | Regra |
| --- | --- |
| Foco | Contorno de 2 px em `--pa-focus`, com afastamento de 3 px |
| Hover | Texto do menu passa a `--pa-text-primary`; botões de watchlist ganham borda `--pa-text-secondary`; resultados da busca ganham fundo `--pa-bg-surface` |
| Ativo | Controle selecionado com fundo `--pa-bg-elevated` e `aria-pressed` |
| Desabilitado | Opacidade de 0,45 e cursor `not-allowed`; no envio de login e cadastro, 0,65 e cursor `wait` |

Uma escala de espaçamento em tokens seria uma mudança visual, que fica para a revisão de
Cláudio; ela não foi criada para não alterar a interface sem decisão.

## 2. Semântica obrigatória

| Situação | Cor | Pista não cromática |
| --- | --- | --- |
| `UP` | `--pa-market-up` | Sinal `+`, seta `▲` e a palavra "alta" |
| `DOWN` | `--pa-market-down` | Sinal `-`, seta `▼` e a palavra "queda" |
| `FLAT` | `--pa-market-flat` | Valor zero, `▬` e a palavra "estável" |
| Variação sem base | `--pa-text-secondary` | Texto "Variação indisponível" |
| Benchmark na comparação | `--pa-market-flat` | Linha tracejada e legenda "referência (benchmark)" |
| `FRESH` | `--pa-accent-neutral` | Rótulo textual |
| `STALE`, `DEMO`, `UNAVAILABLE` | Tokens de estado | Rótulo textual no selo |

A direção vem do **sinal exato do Decimal** da API (`src/lib/price-direction.ts`), sem
epsilon e sem converter para ponto flutuante. Os dígitos não são arredondados.

## 3. Componentes e utilitários

| Peça | Arquivo | Contrato |
| --- | --- | --- |
| Selo de estado | `DataStateBadge` em `market-data.tsx` | `DataLevel` e `Freshness` em texto |
| Painel de proveniência | `ProvenancePanel` em `market-data.tsx` | Fonte, dataset, horários, latência e limitações |
| Variação com direção | `describeChange` em `src/lib/price-direction.ts` | Texto assinado, seta e palavra, ou `null` |
| Avisos legais | `src/lib/disclaimers.ts` | Texto literal da política (§11), testado contra ela |
| Gráfico de série | `particle-chart.tsx` (SVG) | Uma série, uma linha; tabela equivalente |
| Comparação | `multi-asset-comparison.tsx` | `INDEX_100` padrão, escala declarada, tabela alinhada por instante |
| Heatmap básico | `market-heatmap.tsx` | Mesma área, cor pela direção, tabela equivalente com proveniência |
| Global Atlas | `global-atlas.tsx` | Tabela por região, sem preço |
| Tema | `theme-toggle.tsx` e `src/lib/theme.ts` | Escolha salva, sistema e escuro, aplicado antes da hidratação |
| Aviso de limite | `rate-limit-notice.tsx` | 429 acessível, com espera quando informada |

## 4. Regras de interação e acessibilidade

- Contorno de foco de 2 px em `a`, `button`, `input`, `select`, `textarea`, `summary` e
  `[tabindex]`.
- Links dentro de texto são sublinhados.
- Toda página tem `h1`, inclusive no estado de carregamento.
- Nenhuma rota rola na horizontal em 320 px.
- `prefers-reduced-motion` reduz transições sem esconder informação.
- Gráficos e o heatmap sempre têm tabela equivalente.

Prova: `apps/web/e2e/day36-wcag.spec.ts` (axe WCAG 2.2 AA em 11 rotas e nos dois temas)
e o [relatório do Dia 36](ACCESSIBILITY_DAY_36.md).

## 5. Fora do P0

Partículas, Canvas e WebGL, malha e globo do Global Atlas, escala contínua de
intensidade no heatmap e transições avançadas continuam P1, com feature flag e
alternativa sem perda de informação (diretriz §24).
