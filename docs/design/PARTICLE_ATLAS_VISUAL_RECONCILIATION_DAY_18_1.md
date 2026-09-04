# Reconciliação visual Particle Atlas — Dia 18.1

Esta nota reconcilia a diretriz visual permanente com o estado observado após os
Dias 16 a 19. É uma atualização documental retroativa; não introduz feature,
dependência ou mudança de comportamento.

## Estado confirmado

- O shell frontend Particle Atlas existe em `apps/web/src/components/market-data.tsx`.
- Tema escuro e tema claro usam tokens monocromáticos em
  `apps/web/app/globals.css`.
- O gráfico P0 atual usa SVG nativo, com fallback tabular acessível.
- Cadastro, login, sessão opaca e logout existem com cookie `HttpOnly`.
- Watchlists e favoritos privados existem sob `/api/v1/watchlists`, com
  isolamento por proprietário e `canonical_id`.
- Não há provider financeiro real, dado financeiro real ou dataset
  `PUBLIC_APPROVED` ativo.
- Carteiras, P&L e TWR continuam previstos no P0, mas ainda não foram
  implementados.

## Decisões reconciliadas

HTML/CSS/SVG continuam o padrão para UI, gráficos simples, acessibilidade e
estados P0 leves. Canvas 2D pode ser escolhido quando densidade, volume de
pontos, partículas, animações ou transições justificarem essa camada; essa
escolha exige medição e equivalente acessível. Não há motivo para reescrever os
gráficos SVG existentes enquanto eles atenderem performance, acessibilidade e
fidelidade.

`TradingView Lightweight Charts` permanece apenas uma candidata de avaliação e
nunca será fonte de verdade. WebGL/Three.js continua P1, feature-flagged e
restrito a visualizações 3D/Global Atlas avançadas.

“Dataism” é uma referência estética somente para transições de troca de ativo,
período, refresh, navegação e futura revalorização de carteira. Nunca representa
preço, tick, previsão ou volatilidade e deve ser desligado ou reduzido com
`prefers-reduced-motion`.

Carteiras futuras representarão dinheiro real registrado pelo usuário, com
preço médio ponderado, moeda de consolidação, FX, provenance completa, eventos
do ledger e tabela equivalente. A camada artística nunca poderá substituir ou
distorcer esses fatos.

Logos reais permanecem proibidos sem fonte e licença aprovadas; monograma,
ticker e placeholder textual são o padrão atual.

## Escopo preservado

Esta reconciliação não ativa provider, dado real, Canvas, WebGL, biblioteca de
gráficos, carteira, P&L, TWR ou qualquer recomendação financeira.
