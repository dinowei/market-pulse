# Semântica avançada de gráficos Particle Atlas

Esta diretriz é canônica para a representação visual de preços, séries
históricas, comparações, renda fixa, volume, eventos e estados de dados. O
Market Pulse deve evoluir para uma biblioteca de visualizações financeiras; um
gráfico bonito não pode ser um gráfico mentiroso. Toda visualização preserva
fonte, `DataLevel`, `Freshness`, timestamps, escala, unidade, fallback tabular
e ausência de recomendação financeira.

## Princípio de escolha

Plataformas financeiras profissionais escolhem o gráfico conforme a situação:

- linha para preço, patrimônio ou índice;
- candlestick/OHLC para abertura, máxima, mínima e fechamento em janelas curtas;
- barras de volume para intensidade de negociação;
- comparação percentual ou base 100 para escalas diferentes;
- heatmap/treemap para mercado, setor e composição;
- streaming somente quando houver provider e licença de tempo real;
- tabela ou alternativa equivalente para acessibilidade e auditoria.

A camada de renderização recebe dados já validados no fluxo
`backend → OpenAPI → cliente TypeScript gerado → componente Particle Atlas →
renderizador`. Uma biblioteca nunca decide se o dado é real, licenciado, fresh,
exibível ou metodologicamente correto; apenas desenha o contrato aprovado.

## Renderização e biblioteca candidata

`TradingView Lightweight Charts` é candidata P0 para avaliação técnica por ser
leve, open source sob Apache 2.0, baseada em Canvas HTML5 e adequada a linhas,
áreas, barras, candles e histogramas. A adoção exige validação de licença,
bundle, acessibilidade e uma ADR própria; não autoriza provider nem dado real.
HTML/CSS/SVG continuam padrão para UI, gráficos simples, acessibilidade e
estados P0 leves. Canvas 2D é recomendado quando densidade, volume de pontos,
partículas, animações ou transições justificarem a escolha, sempre com medição e
equivalente acessível. Os gráficos SVG P0 existentes não devem ser reescritos
sem evidência de ganho. WebGL/Three.js permanece P1, feature-flagged, apenas
para visualizações 3D/Global Atlas avançadas.

Dataism é somente uma referência para transições de troca de ativo, período,
refresh, navegação e futura revalorização de carteira. Nunca representa preço,
tick, previsão ou volatilidade; não pode bloquear números nem continuar ativa
com `prefers-reduced-motion`.

## Semântica de cores

As cores não têm significado universal fora do contexto do gráfico, período,
ativo e objetivo:

- verde: variação positiva, ganho ou movimento acima da referência;
- vermelho: variação negativa, perda ou movimento abaixo da referência;
- azul: referência, neutralidade, baseline, benchmark, estabilidade ou comparação;
- cinza/branco: série principal neutra quando não se pode inferir tendência;
- âmbar: `STALE`;
- cinza operacional: `UNAVAILABLE`;
- `DEMO`: identificação textual explícita, nunca aparência de dado real.

Verde/vermelho/azul não devem pintar automaticamente uma linha inteira. Toda
codificação de direção também usa texto, sinal, ícone, forma ou padrão. Uma
paleta alternativa azul/laranja pode ser oferecida futuramente, sem retirar os
rótulos textuais nem mudar o significado financeiro. Contraste deve atender
WCAG 2.2 AA.

`FRESH` aparece em texto e provenance, sem uma cor de alerta própria. `STALE`,
`DEMO` e `UNAVAILABLE` exigem rótulo visual claro e explicação textual.

## Janelas curtas e intraday

Para `1m`, `5m`, `15m`, `1H` e intraday rápido, a linha principal é branca,
cinza ou neutra. Verde/vermelho aparecem em segmentos, candles, barras ou
marcadores; não se colore a linha inteira pelo último movimento. Azul é
reservado principalmente a preço anterior, baseline, benchmark, VWAP, CDI ou
referência. Gaps e leilões aparecem como gaps, nunca como linha suavizada; o
volume usa barras separadas quando existir.

| Situação | Gráfico preferido |
| --- | --- |
| Preço intraday simples | Linha neutra com segmentos/markers |
| Alta volatilidade intraday | Candlestick/OHLC |
| Máxima/mínima | OHLC ou candlestick |
| Volume | Barras/histograma |
| Preço contra referência | Linha neutra + baseline azul |
| Microvariações | Pontos, barras ou candles |

## Janelas médias e longas

Para `1D`, `5D`, `1M`, `3M`, `6M`, `YTD`, `1A`, `5A` e `MAX`, verde/vermelho
podem indicar performance acumulada. `INDEX_100` é o padrão para escalas
diferentes, mantendo sempre preço real, moeda e valores originais disponíveis.
Azul pode representar Ibovespa, S&P 500, Nasdaq, CDI, inflação, benchmark ou
base 100. Gaps, quedas e picos não podem ser suavizados; eventos relevantes
podem ser marcadores; a tabela fallback preserva os valores reais.

| Situação | Gráfico preferido |
| --- | --- |
| Histórico simples | Linha |
| Comparação entre ativos | Multilinha com `INDEX_100` |
| Patrimônio de carteira | Linha ou área |
| Rentabilidade acumulada | Linha indexada |
| Queda desde topo | Drawdown |
| Dividendos, splits e resultados | Marcadores de evento |
| Comparação com CDI/índice | Linha principal + benchmark azul |

## Renda fixa

Azul é a cor de referência para taxa contratada, curva de juros, CDI,
benchmark, marcação teórica, preço teórico, taxa de emissão, meta ou indexador.
Verde/vermelho só aparecem para ganho/perda de marcação a mercado, variação do
preço, diferença contra benchmark ou impacto factual no patrimônio. Renda fixa
não deve parecer trade rápido: priorize taxa, vencimento, indexador, marcação e
referência.

## Comparação e `INDEX_100`

Uma linha representa uma série; várias linhas representam vários ativos,
fundos, índices, benchmarks ou carteiras. O padrão multissérie é `INDEX_100`,
mas o usuário pode alternar para preço real quando moeda, unidade, calendário e
metodologia forem compatíveis. Tooltip e tabela mostram valores reais, moeda,
base, fonte e timestamps. O frontend não recalcula metodologia financeira
crítica fora do contrato.

`INDEX_100` transforma o primeiro ponto válido do período em 100 e expressa os
seguintes como variação relativa. Isso compara trajetórias sem sugerir que os
ativos têm o mesmo valor nominal.

## Tempo real e estados

`REAL_TIME` exige provider licenciado, direito de uso por exchange, WebSocket ou
streaming, pub/sub, assinatura de símbolos, rate limit, budget, reconexão,
backpressure e entitlement explícito. Cron, polling rápido, backfill ou refresh
periódico nunca devem ser chamados de tempo real. Enquanto esses requisitos não
existirem, classifique como `DEMO`, `EOD`, `DELAYED`, `STALE` ou
`UNAVAILABLE`, mantendo `DataLevel` e `Freshness` separados.

## Tipos de gráfico e prioridade

| Tipo | Uso | Prioridade |
| --- | --- | --- |
| Linha | Preço, patrimônio ou índice | P0 |
| Multilinha | Comparação de séries | P0 |
| `INDEX_100` | Escalas diferentes | P0 |
| Preço real | Valores nominais | P0 |
| Candlestick/OHLC | Intraday e OHLC disponível | P0/P1 |
| Barras de volume | Volume fornecido pelo provider | P0 |
| Área | Patrimônio e evolução acumulada | P0 |
| Drawdown | Queda desde topo | P1 ou P0 para carteira |
| Eventos | Dividendos, splits e resultados | P0 |
| Tabela fallback | Acessibilidade e auditoria | P0 obrigatório |

Heatmap, treemap, curva de juros, correlação, scatter, waterfall, calendário,
Global Atlas, volume profile e VWAP são P1/futuros. Heatmap/treemap mostram
distribuição, intensidade, peso ou composição; não substituem linha, candle ou
tabela. Cada tile terá fallback textual/tabela e provenance completa.

## Contrato obrigatório de exibição

Todo gráfico recebe ou disponibiliza `canonical_id`, nome/símbolo, tipo de ativo,
bolsa, moeda, período, modo, provider, dataset, `DataLevel`, `Freshness`,
timestamp oficial, timestamp de coleta, latência, ajuste, limitações, pontos e
tabela fallback. Sem esses campos, deve falhar honestamente ou mostrar
`UNAVAILABLE`.

## Regras anti-distorção

É proibido suavizar criando máximas/mínimas, preencher gaps como negociação,
esconder quedas por interpolação, mostrar `DEMO` como real, `EOD` como
`REAL_TIME`, comparar escalas sem declarar o modo, inferir candles/volume,
usar azul como “preço parado” fora de contexto, ou usar logos, nomes de fonte e
dados sem licença. É permitido destacar segmentos, usar OHLC fornecido, linha
neutra em janela curta, azul para benchmark, `INDEX_100`, `STALE` e
`UNAVAILABLE` com explicação textual.

## Aplicação no roadmap

No Dia 16, o shell, temas e componentes apenas preparam esta semântica; o
gráfico final não é requisito. No Dia 17, implementar linha, multilinha,
`PRICE`, `INDEX_100` e fallback tabular, avaliar a biblioteca candidata e
registrar ADR se adotada. Candles entram quando houver OHLC adequado; heatmap e
treemap seguem P1; WebSocket/`REAL_TIME` exige provider licenciado e nova
arquitetura. Nenhuma etapa ativa dado real ou recomendação financeira.
