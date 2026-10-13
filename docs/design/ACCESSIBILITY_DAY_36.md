# Acessibilidade WCAG 2.2 AA e daltonismo (Dia 36)

- **Data:** 2026-10-07 (UTC).
- **Branch:** `feature/dia-31-34`, sem deploy.
- **Fontes:** [diretriz Particle Atlas](PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md) (§8, §9, §20 e
  §23), [ADR-006](../adr/006-monochrome-financial-chart-semantics.md) e
  [ADR-015](../adr/015-oklch-tokens-and-theme-contrast.md).
- **Escopo do roadmap:** axe em todas as rotas, revisão manual e daltonismo validado por
  simulação da paleta existente e pelos sinais não cromáticos. Paleta alternativa
  azul/laranja só com nova ADR; esta revisão **não** a propõe.

## 1. Achados e correções

| # | Achado | Regra | Correção | Prova |
| --- | --- | --- | --- | --- |
| A-1 | A variação do ativo no dashboard era sempre azul (`FLAT`), subisse ou caísse, e só a queda tinha sinal | Diretriz §8 e §9; WCAG 1.4.1 | Direção `UP`/`DOWN`/`FLAT` pelo sinal exato do Decimal, sem epsilon; cada direção tem cor, sinal, seta e palavra; base declarada ("fechamento anterior"); variação absoluta e percentual | `apps/web/app/day36-a11y.test.ts` |
| A-2 | O selo `FRESH` usava o verde de alta | Diretriz §8: "`FRESH` é neutro e textual" | Marca neutra (`--pa-accent-neutral`) | Mesmo teste |
| A-3 | Sem base de comparação, a cotação pública devolvia `change = 0` | Política de integridade: não preencher valor ausente | `change` e `change_percent` nulos ("Variação indisponível"), em vez de um `FLAT` inventado | `apps/api/tests/test_quote_change_day36.py` |
| A-4 | O contorno de foco valia só para `a`, `button` e `input` | Diretriz §20; WCAG 2.4.7 | Mesmo contorno para `select`, `textarea`, `summary` e `[tabindex]` | E2E de teclado (seção 3) |
| A-5 | Em `/login` e `/register`, o link para alternar entre entrar e criar conta só se distinguia do texto pela cor (axe `link-in-text-block`, grave, nos dois temas) | WCAG 1.4.1 | Link sublinhado | E2E axe (seção 3) |
| A-6 | O estado de carregamento de `/watchlists` não tinha `h1` | WCAG 1.3.1 e 2.4.6 | `h1` acessível no carregamento, como em `/portfolios` | E2E de reflow (seção 3) |

## 2. Simulação de daltonismo

**Método:** matrizes de Machado, Oliveira e Fernandes (2009), severidade 1,0, aplicadas
em RGB linear; acromatopsia preserva só a luminância relativa. Distância em OKLab
(`deltaEOK` da CSS Color 4; cerca de 0,02 é a menor diferença perceptível). Código em
`apps/web/src/lib/color.ts`.

**Distância entre as cores de direção** (quanto maior, mais distinguível):

| Tema | Visão | UP × DOWN | UP × FLAT | DOWN × FLAT |
| --- | --- | --- | --- | --- |
| Escuro | normal | 0,331 | 0,241 | 0,276 |
| Escuro | protanopia | 0,237 | 0,221 | 0,209 |
| Escuro | deuteranopia | **0,095** | 0,215 | 0,205 |
| Escuro | tritanopia | 0,361 | **0,081** | 0,334 |
| Escuro | acromatopsia | 0,146 | **0,085** | **0,061** |
| Claro | normal | 0,276 | 0,212 | 0,297 |
| Claro | protanopia | 0,137 | 0,204 | 0,208 |
| Claro | deuteranopia | **0,039** | 0,206 | 0,243 |
| Claro | tritanopia | 0,299 | **0,043** | 0,298 |
| Claro | acromatopsia | **0,046** | **0,050** | **0,004** |

**Leitura:** a paleta não separa as direções sozinha para todas as visões. No tema claro,
alta e queda quase se confundem em deuteranopia, e queda e estável ficam iguais em
acromatopsia. Por isso a informação não depende da cor: sinal (`+`/`-`), seta
(`▲`/`▼`/`▬`) e palavra (alta, queda, estável) acompanham toda direção, e a comparação usa
linha tracejada e legenda em texto para benchmarks (ADR-018).

**Contraste do texto de direção** (WCAG mede as cores reais):

| Tema | Mínimo em visão normal | Mínimo simulado |
| --- | --- | --- |
| Escuro | 6,56:1 (queda sobre elevado) | 5,18:1 (protanopia) |
| Claro | **4,60:1** (alta sobre elevado) | **4,30:1** (protanopia) |

Todos passam o AA de 4,5:1 nas cores reais. O verde de alta do tema claro sobre o fundo
elevado tem a menor margem; escurecê-lo é decisão de direção visual (ADR-015) e fica como
observação para a revisão de Cláudio, não como correção deste dia. O teste exige 4,5:1 em
visão normal e um piso de 3:1 em todas as simulações.

## 3. Varredura automática (axe) e verificações de navegador

`apps/web/e2e/day36-wcag.spec.ts`, Playwright com Chromium e `@axe-core/playwright`, tags
`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` e `wcag22aa`:

- axe nas 9 rotas (`/`, `/login`, `/register`, `/watchlists`, `/portfolios`, `/compare`,
  `/calendar`, `/editorial/admin` e `/admin/system`), nos temas escuro e claro;
- reflow em 320 px de largura sem rolagem horizontal (WCAG 1.4.10);
- 25 paradas de Tab no dashboard, todas com contorno de foco de pelo menos 2 px;
- movimento reduzido mantendo a tabela da comparação.

| Rodada (2026-10-07) | Resultado |
| --- | --- |
| 1ª | 21 falhas por tempo de espera (`networkidle` nunca ocorre; ver limitações). Nenhuma medição. |
| 2ª | 16 passaram; 5 falharam por A-5 (4 testes) e A-6 (1 teste). |
| 3ª, após as correções | **21 passaram** (2,8 min). |

**Limitações desta medição:**

- Rodada local na máquina do responsável, com Docker parado. A API rodou com DEMO
  desligado e sem Postgres e Redis. Por isso, as rotas privadas foram verificadas no
  estado "sem sessão", o Morning Call no estado "carregando" (o endpoint espera o banco)
  e o dashboard sem variação ("Variação indisponível").
- Os estados com sessão e com dados DEMO ficam para a rodada oficial (Dia 39), que exige
  CI com Postgres e Redis (H-05) ou o Docker local.
- A espera usa o estado renderizado (`h1` presente e fim do "Carregando"), não
  `networkidle`, porque os beacons de telemetria podem ficar abertos.

## 4. Revisão manual

A diretriz (§20) diz que axe não substitui a revisão manual. Estado de cada item:

| Item da diretriz §20 | Verificação | Estado |
| --- | --- | --- |
| HTML semântico e `h1` por página | axe e E2E (`h1` em toda rota, inclusive no carregamento) | Automatizado |
| Teclado e foco branco visível | E2E de Tab no dashboard; contorno ampliado (A-4) | Parcial: só o dashboard foi percorrido |
| Contraste de linhas e textos | Testes de tokens (ADR-015) e seção 2 | Automatizado |
| Alvos adequados | axe `target-size` (WCAG 2.5.8, tag `wcag22aa`) | Automatizado |
| Labels acessíveis | axe | Automatizado |
| Tabela ou resumo equivalente | E2E de movimento reduzido e testes dos Dias 31–35 | Automatizado |
| Tooltip por teclado e toque | Não há tooltip no P0 | Não se aplica |
| Sem depender de cor, hover ou animação | A-1, A-5 e seção 2 | Corrigido nos pontos achados |
| Leitor de tela (NVDA ou VoiceOver) | Não executado | **Pendente: revisão humana** |
| Zoom de 200% e espaçamento de texto (WCAG 1.4.4 e 1.4.12) | Não executado | **Pendente: revisão humana** |

O gate do Dia 36 fica com a parte automatizada aprovada e a revisão humana pendente,
junto com a revisão visual de Cláudio prevista desde os Dias 31 a 34.
