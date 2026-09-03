# Particle Atlas — gráficos P0 do Dia 17

O Dia 17 adiciona a primeira visualização de série histórica dentro do shell
Particle Atlas. A página usa exclusivamente os contratos de
`apps/web/src/generated/api.ts` e os endpoints públicos do Dia 15.

## Decisão de renderização

Não foi instalada `lightweight-charts` neste dia. A série P0 usa SVG nativo com
uma linha neutra e marcadores, porque o contrato atual é pequeno, não há
necessidade medida de uma biblioteca adicional e SVG fornece uma superfície
acessível simples. `TradingView Lightweight Charts` continua candidata para
uma avaliação posterior de densidade/performance; qualquer adoção futura exige
revisão de licença, bundle e ADR. WebGL/Three.js não participa do caminho P0.

O SVG é somente apresentação. O backend/OpenAPI/cliente gerado continua a
fonte da verdade para pontos, valores, estados e provenance. A conversão
numérica no componente serve apenas para coordenadas de desenho; não produz
cálculo financeiro, retorno ou recomendação.

## Ativo, busca e contratos

`InstrumentSearch` consulta `GET /api/v1/instruments/search?q=...` e seleciona
por `canonical_id`, exibindo o estado de suporte do catálogo. A seleção alimenta:

- `GET /api/v1/market-data/quotes/{canonical_id}`;
- `GET /api/v1/market-data/history/{canonical_id}`.

Quote e histórico mantêm moeda, provider, dataset, `DataLevel`, `Freshness`,
timestamps, latência, limitações e estado de indisponibilidade. Strings
decimais permanecem strings para exibição.

## Semântica da série

Os controles oferecem `1D`, `5D`, `1M`, `3M`, `6M`, `YTD`, `1A`, `5A` e `MAX`,
além de `PRICE` e `INDEX_100`. `PRICE` escolhe fechamento/valor nominal; o
modo indexado escolhe `index_100` retornado pelo backend. Gaps permanecem
lacunas e pontos nulos não são preenchidos. A linha é neutra, com legenda de
modo e tabela contendo os mesmos pontos; direção não depende somente de cor.

O contrato atual retorna uma série por chamada. A comparação multissérie fica
explicitamente preparada, mas não inventa benchmark nem cria segunda linha sem
uma série real fornecida pelo backend.

## Acessibilidade e estados

O gráfico possui nome acessível e a tabela fallback expõe sessão, fechamento,
índice e gaps. Busca e controles usam labels, botões, `fieldset`, `legend`,
`aria-pressed`, `aria-selected` e foco visível. O CSS respeita
`prefers-reduced-motion`; estados `DEMO`, `STALE` e `UNAVAILABLE` são textuais
e mantêm limitações/provenance visíveis.

## Limites e próximos passos

Candlestick/OHLC, volume, marcadores de eventos, comparação real entre várias
séries, heatmap, treemap, curva de juros e Global Atlas permanecem etapas
posteriores. Nenhum provider, dado real, dataset `PUBLIC_APPROVED`, WebSocket,
carteira, P&L, Morning Call editorial ou recomendação foi ativado.
