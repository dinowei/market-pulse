# Particle Atlas — shell frontend do Dia 16

O Dia 16 entrega a primeira tela funcional do terminal informativo. A
implementação fica em `apps/web/src/components/market-data.tsx` e usa apenas os
tipos gerados em `apps/web/src/generated/api.ts` para dados financeiros.

## Tokens e temas

`apps/web/app/globals.css` define tokens CSS custom properties para canvas,
superfície, borda hairline, texto, foco e estados financeiros. O tema escuro é
o padrão; `data-theme="light"` alterna para a mesma estrutura com fundo claro e
texto escuro. Verde, vermelho e azul são reservados para semântica de mercado;
âmbar identifica stale, cinza identifica indisponibilidade e `DEMO` permanece
textual. Não há gradientes, dourado dominante ou dependência exclusiva de cor.

## Shell e componentes

O `TerminalShell` organiza topo, busca, navegação semântica, rail operacional,
área central de série, painel contextual do ativo e rodapé. Os componentes
`DataStateBadge`, `ProvenancePanel`, `MarketStatusBar`, `AssetContextPanel`,
`PeriodSelector`, `SeriesModeToggle` e `AccessibleDataTable` são pequenos,
tipados e reutilizáveis.

O shell consulta os endpoints do Dia 15 para `equity.br.b3.petr4`:

- `GET /api/v1/market-data/quotes/{canonical_id}`;
- `GET /api/v1/market-data/history/{canonical_id}?period=...&mode=...`.

Loading, erro, vazio, `DEMO`, `STALE` e `UNAVAILABLE` são estados explícitos.
Provider, dataset, moeda, timestamps, latência, `DataLevel`, `Freshness` e
limitações aparecem no painel de proveniência. O fallback tabular preserva
fechamento, `INDEX_100` e gaps retornados pelo contrato; nenhum preço ou ponto
é criado no componente.

## Acessibilidade e responsividade

O layout usa `header`, `nav`, `main`, `aside`, `footer`, `fieldset`, `table`,
labels e nomes acessíveis. Foco visível, tabela equivalente, quebra de colunas
para telas estreitas, `overflow-x` controlado e `prefers-reduced-motion` são
implementados no CSS. A área visual do gráfico é deliberadamente um placeholder
semântico: o gráfico Particle Atlas real pertence ao Dia 17.

## Limites do Dia 16

Não há provider externo, dado real, persistência de preferências, watchlist,
carteira, P&L, Morning Call editorial, heatmap avançado, Canvas, WebGL ou
Three.js. O cliente usa o backend local e pode exibir indisponibilidade quando a
API não estiver disponível. A suíte atual usa `node:test` para contratos de
fonte; axe/Playwright permanecem uma lacuna para os gates de UX posteriores.
