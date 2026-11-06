# Design system do Market Pulse (v3): referência do que está implementado

- **Data:** 2026-10-13 (v3, [ADR-028](../adr/028-visual-identity-v3-chart-workspace.md)).
- **Natureza:** inventário do código em `apps/web` na branch `feature/dia-41-sync`.
- **Norma:**
  - A ADR-028 substitui a parte visual da
    [diretriz Particle Atlas](PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md), da ADR-006 e da ADR-026,
    por decisão do responsável.
  - As regras de dado da [semântica de gráficos](PARTICLE_ATLAS_CHART_SEMANTICS.md)
    continuam valendo: uma série real por linha, `INDEX_100` na comparação, direção com
    pista não cromática e indisponibilidade visível.
  - Em conflito com essas regras, este documento deve ser corrigido.
- **Decisões que o moldaram:** [ADR-005](../adr/005-hybrid-progressive-rendering.md),
  [ADR-015](../adr/015-oklch-tokens-and-theme-contrast.md),
  [ADR-016](../adr/016-global-persisted-theme.md),
  [ADR-019](../adr/019-global-atlas-table-and-basic-heatmap.md),
  [ADR-021](../adr/021-optional-color-vision-palette.md),
  [ADR-028](../adr/028-visual-identity-v3-chart-workspace.md) e
  [ADR-029](../adr/029-owner-real-data-universe.md).

## 1. Tokens

Definidos em `apps/web/app/globals.css`, com o mesmo valor em hex e em `oklch()`
(dentro de `@supports`). O tema vale para todas as páginas em `<html data-theme>`.

| Token | Escuro | Claro | Uso |
| --- | --- | --- | --- |
| `--pa-bg-canvas` | `#0a1020` | `#f2f5fb` | Fundo da página (com brilho radial decorativo no topo) |
| `--pa-bg-surface` | `#111a2e` | `#ffffff` | Painéis, cartões e barra lateral |
| `--pa-bg-elevated` | `#18233c` | `#e8eef8` | Elevação (chips da faixa, blocos do heatmap, menus) |
| `--pa-border-hairline` | `#24324f` | `#cfd8ea` | Grades e divisórias |
| `--pa-border-control` | `#64759c` | `#7a87a3` | Borda de campos (≥ 3:1) |
| `--pa-text-primary` | `#eef2fb` | `#0d1630` | Texto |
| `--pa-text-secondary` | `#a6b2ca` | `#45547a` | Metadados |
| `--pa-accent-neutral` | `#a6b2ca` | `#45547a` | Marca de `FRESH` |
| `--pa-accent` | `#86a3ff` | `#2f4fd6` | Acento: links, linha principal do workspace, item ativo |
| `--pa-accent-strong` | `#3f5ef0` | `#2f4fd6` | Fundo de botão e aba ativos (texto em `--pa-accent-ink`, `#ffffff`) |
| `--pa-violet` | `#b9a0ff` | `#6a45d6` | Acento secundário (marcadores de família, comparação) |
| `--pa-cyan` | `#4cc9f0` | `#0a6d91` | Acento secundário (marcadores de família, comparação) |
| `--pa-market-up` | `#34d399` | `#08784a` | Direção `UP` |
| `--pa-market-down` | `#f87171` | `#c22d2d` | Direção `DOWN` |
| `--pa-market-flat` | `#86a3ff` | `#2f4fd6` | Direção `FLAT` |
| `--pa-state-stale` | `#f5a524` | `#8c5a00` | Só `STALE` e alerta restrito |
| `--pa-state-unavailable` | `#919db6` | `#56648a` | `UNAVAILABLE` |
| `--pa-state-demo` | `#e2e8f5` | `#2b3757` | `DEMO` |
| `--pa-focus` | `#9fb5ff` | `#2f4fd6` | Contorno de foco |

**Contraste (testado):** texto ≥ 4,5:1 e foco e bordas de controle ≥ 3:1 nos dois temas
(`oklch-tokens-day33.test.ts`, `day36-a11y.test.ts`, `theme-global.test.ts`). O menor valor
das cores de direção é 4,75:1 no tema claro (alta, fundo elevado) e 5,65:1 no escuro
(queda, fundo elevado).

### Tipografia, forma e camadas

Também extraídos de `globals.css`. O que não existe está dito como inexistente, em vez de
uma escala sugerida.

| Aspecto | Implementado |
| --- | --- |
| Família | Archivo com eixo de largura (`wdth`), auto-hospedada por `next/font`; títulos e números largos (`wdth` 108 a 122) |
| Pesos | 400 a 800 (`600` e `700` nos rótulos e botões, `800` em títulos e valores) |
| Números | Algarismos tabulares nas tabelas, no preço, no panorama e nas métricas da carteira |
| Rótulos | Caixa normal (sem caixa alta) |
| Raio | `--pa-radius: 12px` em painéis e cartões; `10px` nos itens do menu lateral; `999px` em controles, chips e selos |
| Profundidade | Sombra suave nos painéis (`--pa-shadow`) e brilho radial decorativo no fundo |
| Breakpoints | `max-width: 1180px` (painel e ativo em uma coluna), `1023px` (barra lateral vira faixa no topo), `700px` e `520px` |
| Estrutura | Barra lateral fixa com as seções "Mercado" e "Sua área"; barra superior com busca global e faixa de referências focável |
| Camadas | `z-index: 30` nos resultados da busca; menus do workspace dentro da área do gráfico |

**Estados de interação:**

| Estado | Regra |
| --- | --- |
| Foco | Contorno de 2 px em `--pa-focus`, com afastamento de 3 px |
| Hover | Item do menu lateral ganha fundo `--pa-bg-elevated`; controles ganham borda `--pa-border-control`; cartões do panorama ganham borda `--pa-accent` |
| Ativo | Controle selecionado com fundo `--pa-accent-strong`, texto `--pa-accent-ink` e `aria-pressed`; página atual no menu com fundo tingido, barra de acento e `aria-current` |
| Desabilitado | Opacidade de 0,45 e cursor `not-allowed`; no envio de login e cadastro, 0,65 e cursor `wait` |

**Paleta opcional para daltonismo** (`<html data-palette="cvd">`, [ADR-021](../adr/021-optional-color-vision-palette.md)): escuro `UP #bddbb6`, `DOWN #d27668`, `FLAT #4f8ff5`; claro `UP #007d1e`, `DOWN #5e3532`, `FLAT #173f81`. Mesmas famílias de cor, separadas pela luminosidade; o workspace usa os mesmos valores.

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
| Estrutura do app | `AppShell` em `site-header.tsx` | Barra lateral, busca global (`instrument-search.tsx`), faixa de referências e botões de tema e paleta |
| Workspace de gráficos | `chart-workspace.tsx` e `src/lib/chart-workspace/` | Canvas (Lightweight Charts 5.2.1): 10 tipos, indicadores, comparação em base 100, 15 ferramentas de desenho salvas por ativo, tabela equivalente e avisos de dado derivado ([ADR-028](../adr/028-visual-identity-v3-chart-workspace.md)) |
| Panorama "Mercados agora" | `market-panorama.tsx` e `src/lib/panorama.ts` | Seis famílias; cotação ou benchmark da API, variação com pista não cromática, linha de 3 meses e motivo quando falta dado ([ADR-029](../adr/029-owner-real-data-universe.md)) |
| Ícones | `icons.tsx` | Traço de 24 px desenhado para o projeto; sempre ao lado de texto ou com nome acessível |
| Selo de estado | `DataStateBadge` em `data-table.tsx` (reexportado por `market-data.tsx`) | `DataLevel` e `Freshness` em texto |
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

O Canvas entrou no workspace de gráficos pela
[ADR-028](../adr/028-visual-identity-v3-chart-workspace.md), sempre com a tabela
equivalente. Continuam P1 o WebGL, a malha e o globo do Global Atlas e a escala contínua de
intensidade no heatmap. O pulso de partículas e as transições do gráfico existem desde a
[ADR-023](../adr/023-markets-hub-chart-type-and-motion.md), também como P1: atrás de
`NEXT_PUBLIC_ATLAS_MOTION`, com alternativa em texto e tabela, sem perda de informação.
