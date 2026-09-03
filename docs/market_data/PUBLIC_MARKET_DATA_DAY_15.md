# Market data público — Dia 15

O Dia 15 torna consumíveis as leituras públicas de catálogo, quote e série,
usando exclusivamente fixtures sintéticas locais. Nenhum provider externo ou
dataset `PUBLIC_APPROVED` foi ativado.

## Endpoints

- `GET /api/v1/instruments` mantém o contrato de listagem; `GET
  /api/v1/instruments/search?q=...` consulta símbolo, nome, alias e
  `canonical_id`. Cada item informa `canonical_id`, exchange, moeda, timezone,
  aliases e estado de suporte, sem preço.
- `GET /api/v1/market-data/quotes/{canonical_id}` retorna quote sintética
  `DEMO`/`STALE` apenas para P0 operacional. Candidatos ou identidades
  bloqueadas retornam `UNAVAILABLE`; identidade inexistente retorna Problem
  Details. Todos os estados carregam provider, dataset, timestamps, latência,
  limitações e `request_id`.
- `GET /api/v1/market-data/history/{canonical_id}` aceita `1D`, `5D`, `1M`,
  `3M`, `6M`, `YTD`, `1A`, `5A` e `MAX`, além de `PRICE`/`INDEX_100` e tipos de
  ajuste explícitos. Pontos são ordenados, sem interpolação ou suavização,
  preservando preço bruto no fallback tabular.

## Particle Atlas e acessibilidade

O contrato de série inclui `tabular_fallback`, `accessibility.reduced_motion` e
`smoothed=false`. `INDEX_100` usa o primeiro ponto válido como base 100, sem
remover `close`/`value` reais. Uma série continua sendo uma linha; comparação
multissérie fica preparada para etapa posterior.

## Limitações conscientes

As fixtures são sintéticas e permanecem `DEMO`; não representam cotação real.
Quotes, históricos e catálogo ainda são leituras em memória, sem ingestão
persistente. Ausência de dataset aprovado nunca é convertida em preço. A UI
completa, heatmap e integração de carteiras permanecem nos Dias 16–19.
