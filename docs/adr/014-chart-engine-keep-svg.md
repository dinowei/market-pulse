# ADR-014: Motor gráfico P0 continua em SVG; Lightweight Charts avaliada e não adotada

- Status: Accepted
- Data: 2026-10-07
- Decisores: responsável técnico (Claude Code), com autorização explícita do operador para
  o Dia 32 da Fase 2. A direção visual continua com Cláudio, e a aprovação final é do
  responsável humano.
- Relação: diretriz Particle Atlas §18 ("Não se deve reescrever os gráficos SVG P0 atuais
  enquanto SVG atender performance, acessibilidade e fidelidade") e semântica de gráficos
  ("A adoção exige validação de licença, bundle, acessibilidade e uma ADR própria").

## Contexto

O Dia 32 pedia a decisão entre TradingView Lightweight Charts e o renderizador próprio,
com validação de `Decimal` e do rótulo `INDEX_100` em relação ao TWR.

## Medição (2026-10-07)

`apps/web/scripts/chart-benchmark.tsx` renderiza o `ParticleChart` real com séries
sintéticas (Node v24.21.0, `renderToStaticMarkup`, 15 execuções por tamanho):

| Pontos | Elementos SVG | Markup | Mediana | P95 |
|---|---|---|---|---|
| 440 (DEMO atual) | 442 | 54,2 KB | 13,2 ms | 22,8 ms |
| 500 (limite do Dia 31) | 502 | 61,6 KB | 13,3 ms | 15,2 ms |
| 1.250 (5A) | 1.252 | 153,5 KB | 9,6 ms | 44,2 ms |
| 2.600 (MAX completo) | 2.602 | 318,8 KB | 17,1 ms | 21,5 ms |
| 10.000 | 10.002 | 1.224,7 KB | 97,7 ms | 357,2 ms |

**Limites da medição:** é o custo de renderização React e o peso do SVG; layout e pintura
no navegador não foram medidos nesta máquina (3,7 GB de RAM). Os budgets do Dia 27 (P95
LCP 2.500 ms, INP 200 ms, CLS 0,10) seguem como gate no ambiente real (Dia 38).

**Fontes oficiais da candidata:** registro npm (`lightweight-charts` 5.2.1, Apache-2.0,
3.095.012 bytes desempacotados, dependência `fancy-canvas`) e repositório
`github.com/tradingview/lightweight-charts`. A licença exige o aviso de atribuição do
arquivo NOTICE e um link para tradingview.com nas páginas que exibem o gráfico. O
renderizador é Canvas HTML5.

## Decisão

1. **Manter o SVG P0.** Com o limite de 500 pontos do Dia 31 (ADR-013), o custo é
   limitado (~500 elementos, ~62 KB, P95 ~15 ms). Só uma série de 10.000 pontos sem
   redução se aproxima do budget de INP, e esse caso não ocorre com a redução.
2. **Não adotar Lightweight Charts agora.** Não há ganho medido. Além disso: a marca de
   terceiro obrigatória em toda página com gráfico conflita com a identidade própria
   (diretriz §6); o Canvas exige equivalente acessível separado; e a biblioteca entraria
   no bundle P0 sem necessidade.
3. **`Decimal`:** valores atravessam a API como string `Decimal`; o componente converte
   para número **apenas** para calcular coordenadas de desenho. Tabela, rótulos e
   proveniência usam a string original. Isso vale para qualquer motor futuro, que nunca é
   fonte de verdade.
4. **Rótulo:** a legenda do modo `INDEX_100` passa a dizer "Índice 100 — preço rebaseado a
   100 no início do período; não é rentabilidade (TWR)". O TWR continua exclusivo das
   carteiras (ADR-007).

## Quando revisar

Ao implementar candles ou volume intradiário com OHLC licenciado, mais de 6 séries
simultâneas, crosshair interativo denso, ou se o gate de Web Vitals do Dia 38 medir
INP acima do budget no gráfico. Qualquer biblioteca nova exige nova ADR; o teste
`app/chart-engine-day32.test.ts` impede a entrada silenciosa no bundle.
