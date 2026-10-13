# ADR-028: Identidade visual v3 e workspace de gráficos

- Status: Accepted
- Data: 2026-10-12
- Decisores: responsável humano pelo produto (pediu, em 2026-10-12, um site "mais bonito",
  com cor e com as ferramentas de um terminal de gráficos, deixando de lado as diretrizes
  do Atlas); implementação por Claude Code
- Relação:
  - substitui, na parte visual, a [diretriz Particle Atlas](../design/PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md),
    a [ADR-006](006-monochrome-financial-chart-semantics.md) (visual monocromático) e a
    [ADR-026](026-particle-atlas-visual-system-v2.md) (sistema visual v2);
  - substitui a [ADR-014](014-chart-engine-keep-svg.md) para o gráfico do painel e da
    página do ativo;
  - mantém a [ADR-015](015-oklch-tokens-and-theme-contrast.md), a
    [ADR-016](016-global-persisted-theme.md) e a
    [ADR-021](021-optional-color-vision-palette.md).

## Contexto

O responsável achou o site "feio, sem cor" e com poucas funcionalidades. Ele mostrou como
referência os menus de desenho, tipos de gráfico e a visão geral de mercados de uma
plataforma de gráficos conhecida, três painéis de fintech e uma pesquisa em PDF sobre
plataformas financeiras. A pesquisa recomenda Canvas em vez de SVG para séries densas,
cache no cliente e desenhos salvos por ativo.

A diretriz Particle Atlas pedia uma interface quase toda em preto, branco e cinza. A
ADR-014 manteve o gráfico em SVG. As duas decisões conflitam com o pedido. Pela hierarquia
do `AGENTS.md`, a instrução direta do operador vem primeiro, e a mudança material exige
esta ADR.

O que **não** muda: as regras de integridade de dados, a política de conteúdo financeiro e
a acessibilidade (WCAG 2.2 AA).

## Decisão

1. **Paleta v3.** Base azul-tinta, acento cobalto (`--pa-accent`, `--pa-accent-strong`),
   violeta (`--pa-violet`) e ciano (`--pa-cyan`), com raio de 12 px e sombra suave nos
   painéis.
   - Os tokens seguem em OKLCH com fallback em hex.
   - O contraste continua testado nos dois temas e na paleta para daltonismo.
   - Verde, vermelho e azul continuam reservados à direção (`UP`, `DOWN`, `FLAT`), sempre
     com sinal, glifo e palavra.
   - O âmbar continua só para `STALE`.
2. **Tipografia.** Archivo, com eixo de largura (`wdth`), auto-hospedada por `next/font`.
   Os rótulos usam caixa normal, não caixa alta.
3. **Estrutura.**
   - Barra lateral com as seções "Mercado" e "Sua área".
   - Busca global de instrumentos e faixa de referências no topo. A faixa rola na
     horizontal e recebe foco pelo teclado.
   - Abaixo de 1024 px, a barra lateral vira uma faixa no topo.
4. **Workspace de gráficos** no painel e na página do ativo, com
   [Lightweight Charts](https://github.com/tradingview/lightweight-charts) 5.2.1
   (Apache-2.0, Canvas).
   - A biblioteca é carregada sob demanda e a marca de atribuição fica ligada.
   - **Tipos de gráfico:** 10, entre velas, barras, linha, área, linha de base e colunas.
   - **Indicadores:** volume, médias móveis simples e exponencial, Bollinger, IFR e MACD
     (os dois últimos em painéis próprios).
   - **Comparação:** em base 100 (`INDEX_100`), uma linha por série real.
   - **Desenho:** 15 ferramentas, com ímã, desfazer, lista de objetos e atalhos. Os
     desenhos ficam salvos por ativo no navegador, com o prefixo `market-pulse.chart.`.
   - **Outros:** captura de tela, tela cheia, períodos e intervalos diário, semanal e
     mensal.
5. **Integridade no workspace.**
   - Heikin Ashi, médias e osciladores são calculados no navegador a partir da série
     servida, e a tela diz que são derivados.
   - Uma série sem OHLC não vira vela: o tipo cai para linha e a tela explica o motivo.
   - Volume ausente não vira zero.
   - Uma série indisponível mostra o motivo (`SESSION_REQUIRED`, `LICENSE_BLOCKED` e
     outros), nunca um gráfico vazio sem explicação.
6. **Acessibilidade.**
   - O gráfico é um `figure` com descrição textual, porque contém o link de atribuição.
   - A tabela com os mesmos dados fica logo abaixo.
   - Links em texto são sublinhados.
   - Os testes de axe, reflow, teclado e movimento reduzido continuam como gate.
7. **Orçamentos mantidos:** até 200 KB gzip de JS por rota e até 10 KB de CSS na primeira
   carga. O CSS do workspace e o do panorama vão em chunks carregados depois.

## Consequências

- **Primeira impressão:** o produto deixa de parecer monocromático. A revisão visual
  humana (Cláudio e responsável) passa a valer para a v3.
- **Diretriz Particle Atlas:** passa a ser histórica na parte visual. As regras de dado
  (proveniência, horário, `DataLevel`, `Freshness`, indisponibilidade visível) continuam
  obrigatórias.
- **SVG P0 (ADR-014):** continua na comparação (`/compare`) e na curva da carteira, onde já
  atende. O Canvas fica no workspace.
- **Dependência nova:** `lightweight-charts` precisa de revisão de versão e licença no
  supply chain, como qualquer pacote.
- **Pendente:**
  - revisão com leitor de tela do workspace;
  - teste de usabilidade das ferramentas de desenho em toque;
  - medição de Web Vitals no staging com a v3.

## Alternativas consideradas

- **Copiar a interface da plataforma de referência:** descartada. Foram reproduzidas as
  funções, não o código, a marca nem os ativos visuais.
- **Manter o SVG próprio e acrescentar ferramentas:** descartada pelo custo e pelo
  desempenho com séries longas, como a pesquisa aponta.
- **Biblioteca de gráficos comercial:** descartada pela licença e pelo custo.
