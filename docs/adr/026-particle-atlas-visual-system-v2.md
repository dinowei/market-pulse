# ADR-026: Sistema visual v2 do Particle Atlas

- Status: Accepted
- Data: 2026-10-11
- Decisores: responsável humano pelo produto (pediu "o site todo bonito, não só os
  gráficos"); implementação por Claude Code
- Relação: [diretriz Particle Atlas](../design/PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md) §7, §8 e
  §18; [ADR-015](015-oklch-tokens-and-theme-contrast.md);
  [matriz de referências](../design/DESIGN_REFERENCE_MATRIX_DAY_41.md)

## Contexto

O site tinha cabeçalho só no dashboard, fonte Arial, painéis lisos e controles quadrados.
O responsável achou "tudo branco e preto", sem acabamento.

A diretriz (§8) manda preto, grafite, branco e cinzas predominarem e reserva verde,
vermelho e azul para a direção do mercado. As referências enviadas também são
monocromáticas. A beleza tem de vir de composição e textura, não de uma cor de identidade
nova.

## Decisões

1. **Cabeçalho único** (`site-header.tsx`) em todas as páginas, menos login e cadastro.
   - **Duas faixas:** marca, busca e botões de exibição no alto; o menu numa faixa de
     largura total.
   - **Página atual:** marcada com `aria-current` e um traço inferior, não só com cor.
   - **Atalho:** um link de pular para o conteúdo, e todo `<main>` tem
     `id="main-content"`.
2. **Tipografia:**
   - **IBM Plex Sans** (400 e 600), auto-hospedada pelo `next/font`, sem chamada externa
     em tempo de execução.
   - **Rótulos, números, cabeçalhos de tabela e selos:** pilha monoespaçada do sistema
     (`ui-monospace`, Consolas, Menlo), sem segunda fonte para baixar.
   - **Títulos:** h1 em peso regular com espaçamento negativo.
3. **Textura:**
   - **Fundo:** uma grade de pontos com brilho frio no topo.
   - **"Planície" de pontos:** em perspectiva, atrás do título de cada página, como em
     `.standalone-page::before` e `.main-panel::before`.
   - **Natureza:** pura textura. Não representa série, relação nem valor, e some com
     `overflow-x: clip` sem gerar rolagem.
4. **Painéis:** superfície em camadas (gradiente sutil no topo) e marcas técnicas nos
   quatro cantos, como nas molduras das referências.
5. **Controles:** pílulas. O ativo é invertido (fundo claro e texto escuro), o que muda o
   contraste e a forma, não a cor.
6. **Orçamento:**
   - JS segue até 200 KB gzip por rota: o maior ficou em 189 KB.
   - CSS da primeira carga fica em até 10 KB gzip: ficou em 10 KB.
   - Para caber, as regras sobrescritas foram fundidas nas originais. O gate de
     desempenho não foi alterado.

## Consequências

- **Tokens novos por tema:** `--pa-dot`, `--pa-glow`, `--pa-floor-dot`, `--pa-panel-top`,
  `--pa-tick`, `--pa-header-bg`, `--pa-row-hover` e `--pa-mono`.
- **Design system:** o [design system](../design/DESIGN_SYSTEM.md) deixa de dizer "sem
  sombra" e "Arial".
- **Cor de destaque:** se o responsável quiser uma cor de destaque além das de direção,
  ela exige mudar a diretriz §8 numa nova ADR, porque o azul é reservado para FLAT e
  referência, e o âmbar para STALE.
