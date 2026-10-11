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
| Família | IBM Plex Sans no corpo (`next/font`, auto-hospedada); pilha monoespaçada do sistema (`--pa-mono`) em rótulos, números, cabeçalhos de tabela e selos ([ADR-026](../adr/026-particle-atlas-visual-system-v2.md)) |
| Pesos | 400 e 600 |
| Números | Algarismos tabulares em todas as tabelas, no preço e nas métricas da carteira |
| Títulos | `h1`: `clamp(1.5rem, 3vw, 2.5rem)`, altura de linha 1,1; `h2`: `1rem` |
| Texto auxiliar | Entre `.66rem` e `.85rem`; os mais usados são `.68rem`, `.72rem` e `.75rem` |
| Altura de linha | 1,1 (títulos), 1,45 e 1,5 (texto corrido) |
| Espaçamento | **Sem escala formal**: valores em `rem` por componente; o mais comum é `1rem`, e as páginas usam `clamp(1rem, 4vw, 3rem)` de margem interna |
| Raio | `--pa-radius: 4px` em painéis; `999px` em controles, menu e selos |
| Profundidade | Sem sombra projetada: camadas de fundo, gradiente sutil no topo dos painéis, marcas técnicas nos cantos e textura de pontos no fundo (decorativa) |
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

**Paleta opcional para daltonismo** (`<html data-palette="cvd">`, [ADR-021](../adr/021-optional-color-vision-palette.md)): escuro `UP #bddbb6`, `DOWN #c4685a`, `FLAT #3f82f0`; claro `UP #007d1e`, `DOWN #5e3532`, `FLAT #173f81`. Mesmas famílias de cor, separadas pela luminosidade.

## 2. Semântica obrigatória

| Situação | Cor | Pista não cromática |
| --- | --- | --- |
| `UP` | `--pa-market-up` | Sinal `+`, seta `▲` e a palavra "alta" |
| `DOWN` | `--pa-market-down` | Sinal `-`, seta `▼` e a palavra "queda" |
| `FLAT` | `--pa-market-flat` | Valor zero, `▬` e a palavra "estável" |
| Candle | Direção da própria barra | Corpo vazado (alta), cheio (queda) ou traço (estável), com legenda |
| Partícula do pulso | Direção da série | Triângulo para cima, triângulo para baixo, barra ou anel vazio (sem variação conhecida) |
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
| Gráfico de série | `particle-chart.tsx` (SVG) | Uma série, uma linha; candles só com OHLC completo em PRICE; grade pontilhada de referência, sem rótulo de valor; tabela equivalente (com OHLC e volume nos candles) |
| Tipo de gráfico | `chart-type-toggle.tsx` e `src/lib/chart-geometry.ts` | Linha ou Candles; Candles desabilitado com o motivo em texto |
| Comparação | `multi-asset-comparison.tsx` | `INDEX_100` padrão, escala declarada, tabela alinhada por instante |
| Heatmap básico | `market-heatmap.tsx` | Mesma área, cor pela direção, tabela equivalente com proveniência |
| Global Atlas | `global-atlas.tsx` | Tabela por região, sem preço |
| Tema | `theme-toggle.tsx` e `src/lib/theme.ts` | Escolha salva, sistema e escuro, aplicado antes da hidratação |
| Aviso de limite | `rate-limit-notice.tsx` | 429 acessível, com espera quando informada |
| Página de ativo | `asset-detail.tsx` (`/assets?id=`) | Componentes do dashboard e só ações com endpoint |
| Proventos do ativo | `asset-events.tsx` | `UNAVAILABLE` com motivo; tabela com origem |
| Filtro por classe | `asset-class-filter.tsx` e `src/lib/asset-classes.ts` | Classes vindas da API; Fundos e Renda fixa indisponíveis com motivo |
| Paleta para daltonismo | `palette-toggle.tsx` e `src/lib/theme.ts` | Opcional, desligada por padrão ([ADR-021](../adr/021-optional-color-vision-palette.md)) |
| Conta | `account-panel.tsx` | Exportação; exclusão com confirmação digitada |
| Hub de mercados | `markets-hub.tsx` e `src/lib/markets.ts` (`/markets?tab=`) | Uma aba por família (padrão WAI-ARIA); famílias sem dataset com motivo e sem número; seleção para comparar ([ADR-023](../adr/023-markets-hub-chart-type-and-motion.md)) |
| Pulso do mercado | `market-pulse-field.tsx` | Arte P1 derivada das linhas: uma partícula por série, tamanho igual, `aria-hidden`, contagem em texto, botão para desligar |
| Movimento | `src/lib/atlas-motion.ts` e classe `.atlas-motion` | Só em transição (ativo, período, modo, tipo, aba, atualização); a linha se desenha e os pontos surgem na ordem da série; `NEXT_PUBLIC_ATLAS_MOTION=off` remove; desligado com `prefers-reduced-motion` |

## 4. Regras de interação e acessibilidade

- Contorno de foco de 2 px em `a`, `button`, `input`, `select`, `textarea`, `summary` e
  `[tabindex]`.
- Links dentro de texto são sublinhados.
- Toda página tem `h1`, inclusive no estado de carregamento.
- Nenhuma rota rola na horizontal em 320 px.
- `prefers-reduced-motion` reduz transições sem esconder informação.
- Gráficos e o heatmap sempre têm tabela equivalente.

Prova: `apps/web/e2e/day36-wcag.spec.ts` (axe WCAG 2.2 AA em 15 rotas e nos dois temas;
reflow em 320, 375, 640, 768 e 1024 px; teclado das abas de mercados; movimento que para
depois da transição). Referências visuais: [matriz do Dia 41](DESIGN_REFERENCE_MATRIX_DAY_41.md).
e o [relatório do Dia 36](ACCESSIBILITY_DAY_36.md).

## 5. Fora do P0

Canvas e WebGL, malha e globo do Global Atlas, escala contínua de intensidade no heatmap
continuam P1. O pulso de partículas e as transições do gráfico existem desde a
[ADR-023](../adr/023-markets-hub-chart-type-and-motion.md), também como P1: atrás de
`NEXT_PUBLIC_ATLAS_MOTION`, com alternativa em texto e tabela, sem perda de informação
(diretriz §24).
