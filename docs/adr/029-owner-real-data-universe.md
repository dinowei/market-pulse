# ADR-029: Universo de dados reais do responsável e panorama de mercados

- Status: Accepted
- Data: 2026-10-13
- Decisores: responsável humano pelo produto (pediu mais funcionalidades e uma visão geral
  de mercados como a da plataforma de referência; "o restante você pode decidir");
  implementação por Claude Code
- Relação:
  - amplia a [ADR-027](027-owner-private-real-data-staging.md), sem mudar a aprovação nem
    quem vê o dado;
  - revê a [ADR-023](023-markets-hub-chart-type-and-motion.md) na parte "VALE3 e CMIN3 só
    com metadados";
  - usa a camada da [ADR-025](025-provider-registry-and-lifecycle.md).

## Contexto

Com a ADR-027, só quatro ids tinham dado real: PETR4, Ibovespa, AAPL e USD/BRL. A página
mostrava pouco além disso. O responsável pediu mais ativos e uma visão geral de mercados
com cripto, câmbio, juros, inflação e commodities.

Em 2026-10-13, uma chamada por recurso, com as chaves do `.env` local e sem expor valores,
mostrou o que os planos atuais servem:

| Fonte | Responde | Recusa |
| --- | --- | --- |
| Twelve Data | cotação e série diária de BTC/USD, ETH/USD, EUR/USD, USD/BRL e XAU/USD; cotação de MSFT, NVDA e SPY | WTI, Brent, gás, prata e cobre como pares, índices (SPX, IXIC, DJI) e B3 (404) |
| brapi | cotação de VALE3, ITUB4, WEGE3, CMIN3, BOVA11, MXRF11 e AAPL34; série sem ajuste de PETR4, VALE3 e ITUB4 | série de WEGE3, CMIN3, BOVA11, MXRF11 e AAPL34, cripto, séries macro (Selic, CDI, IPCA) e múltiplos (403) |
| Alpha Vantage | WTI mensal (`name`, `unit`, `data[{date, value}]`) | — |
| Massive | — | índices (`I:SPX`, 403) |

O teste opcional `tests/test_live_providers_optin.py` repetiu as chamadas que viraram
código: das 29, 24 responderam e as 5 séries da B3 fora do plano voltaram 403, como
esperado.

## Decisão

1. **Catálogo.** Entram ITUB4, WEGE3, BOVA11, MSFT, NVDA, SPY, ETH/USD, USD/BRL, EUR/USD e
   ouro (XAU/USD).
   - BTC/USD, VALE3, CMIN3 e AAPL34 passam de "só metadados" para `PROVIDER_PENDING`.
   - Todos ficam como `CANDIDATE` no nível `P1`.
   - O universo operacional P0 continua sendo PETR4 e AAPL.
2. **Quem vê.** O mesmo da ADR-027:
   - **Sessão do responsável:** dado real.
   - **Sem sessão:** `SESSION_REQUIRED`.
   - **Ambiente protegido sem fonte:** `PROVIDER_NOT_CONFIGURED`.
   - **Local e testes:** DEMO, que só cobre o P0; os novos ids ficam `UNAVAILABLE` (`DATASET_NOT_APPROVED`).
3. **Precedência nova.** Pares de câmbio, cripto e metal usam só a Twelve Data, para
   cotação e série diária.
   - O benchmark USD/BRL continua na Open Exchange Rates.
   - A página do par passa a ter cotação e série pela Twelve Data. Cada resposta diz a sua
     fonte; nenhuma mistura as duas.
4. **Pares sem moeda.** A Twelve Data não envia `currency` para pares.
   - A moeda é a cotada do par (`BTC/USD` → USD), conferida contra o catálogo.
   - Moeda divergente vai para quarentena, como antes.
   - Um ticker comum continua exigindo o campo `currency`.
5. **Mercado de 24 horas.** Câmbio, cripto e ouro trazem o aviso de que a barra diária vai
   de 00:00 a 24:00 UTC e de que a de hoje ainda está em formação.
6. **Recusa não é falha.** Uma recusa de consulta (`LICENSE_BLOCKED`, `SCHEMA_UNSUPPORTED`)
   não conta para abrir o circuit breaker do provider.
   - **Motivo:** três históricos recusados da brapi bloqueavam todas as cotações da brapi
     por 5 minutos.
   - A recusa segue lembrada por 1 h, só para aquela consulta.
7. **Panorama "Mercados agora"** no painel, com seis grupos: Brasil, Estados Unidos, câmbio,
   cripto, commodities, juros e inflação.
   - Cada cartão mostra a cotação ou o benchmark da API, a variação do dia (sinal, glifo e
     palavra) e uma linha de 3 meses com a variação do período, calculada dos fechamentos
     da própria linha.
   - Cartão sem dado mostra o motivo e o código.
   - Benchmark sem unidade declarada (H-30) não ganha sufixo de moeda.
   - As cotações vêm em lotes de 10 e as linhas de 3 em 3, para não estourar as cotas num
     cache frio.
8. **Hub de mercados.** O tipo `FX` vai para a aba Câmbio e o tipo `COMMODITY` para a nova
   aba Commodities.

## Consequências

- **Cobertura:** o painel do responsável passa de 4 para 18 ids com dado real possível.
  Continuam sem fonte: S&P 500, Nasdaq, IFIX, CDI e IPCA.
- **Cotas:** a cota por minuto da Twelve Data (7) pode recusar parte das consultas num
  cache frio. As ações dos EUA caem para a Massive e para a Alpha Vantage; câmbio, cripto e
  ouro ficam `RATE_LIMITED` até a próxima janela.
- **Gráfico sem histórico:** WEGE3, CMIN3, BOVA11, MXRF11 e AAPL34 têm cotação, mas o
  plano da brapi recusa a série; o gráfico mostra `LICENSE_BLOCKED`.
- **Risco de licença:** o mesmo da ADR-027. O registro da Twelve Data descreve o plano
  Basic como "Internal non-display usage". O risco cresce com mais ativos exibidos,
  mesmo restritos à sessão do responsável.
- **Pendente:**
  - commodities além do ouro, pela Alpha Vantage, que precisam de uma série só de
    fechamento;
  - juros e inflação, que dependem de plano pago da brapi;
  - revisão dos termos das cinco fontes antes de qualquer exposição pública.

## Alternativas consideradas

- **Banco Central (SGS) para Selic, CDI e IPCA:** descartada. O pedido do responsável
  excluiu "providers sem credencial" e fontes sem licença aprovada.
- **Montar uma barra OHLC a partir de um único valor (commodities da Alpha Vantage):**
  descartada; seria inventar abertura, máxima e mínima.
- **Usar o ETF SPY como "S&P 500":** descartada. O SPY aparece com o próprio nome, e o
  índice continua indisponível.
