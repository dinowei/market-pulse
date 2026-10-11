# MASTER_INSTRUMENT_CATALOG

Catálogo estático amplo, normalizado a partir da lista inicial fornecida para o Dia 8. A importação de referência contém 727 linhas de instrumentos; duplicatas foram tratadas por categoria e símbolo. Nenhum registro contém preço, volume, variação ou histórico.

Existir neste catálogo significa somente possuir metadados. Não implica provider, licença, cobertura ou dado real. Os registros importados começam como `CANDIDATE`, `FUTURE_REVIEW` e `METADATA_ONLY` até aprovação explícita.

| Categoria | Exemplos normalizados | catalog_status | coverage_tier | data_support_status |
| --- | --- | --- | --- | --- |
| BR ações/equities | ABEV3, PETR4, VALE3, ITUB4 | CANDIDATE | FUTURE_REVIEW | METADATA_ONLY |
| BR ETFs | BOVA11, IVVB11 | CANDIDATE | FUTURE_REVIEW | METADATA_ONLY |
| BR FIIs | MXRF11, HGLG11 | CANDIDATE | P0_CATALOG/FUTURE_REVIEW | LICENSE_PENDING |
| EUA ações/equities | AAPL, MSFT, AMZN, NVDA | CANDIDATE | FUTURE_REVIEW | METADATA_ONLY |
| EUA ETFs | SPY, QQQ, VTI | CANDIDATE | FUTURE_REVIEW | METADATA_ONLY |
| Índices | IBOV, SPX, IXIC | CANDIDATE | P0_CATALOG | PROVIDER_PENDING |
| FX | USD/BRL, EUR/USD | CANDIDATE | P0_CATALOG | PROVIDER_PENDING |
| Commodities | GOLD, BRENT, WTI | CANDIDATE | P0_CATALOG | PROVIDER_PENDING |
| BDRs | AAPL34, N1DA34 | CANDIDATE | FUTURE_REVIEW | METADATA_ONLY |
| Cripto | BTC/USD, ETH/USD | CANDIDATE | FUTURE_REVIEW | METADATA_ONLY |

Cada instrumento deve persistir `canonical_id`, `symbol`, `display_symbol`, `name`, `instrument_type`, `exchange`/`venue`, `country`/`region`, `currency`, timezone IANA, `aliases`, `catalog_status`, `coverage_tier`, `data_support_status` e `notes`. O ticker isolado nunca é identidade principal; exemplos de IDs estáveis: `equity.br.b3.petr4`, `equity.us.nasdaq.aapl`, `etf.br.b3.ivvb11`, `fx.global.usd-brl`.

## Estado no código (conferido em 2026-10-11)

A importação de 727 linhas descrita acima **não existe no código**. `MASTER_CATALOG`, em
`apps/api/app/instruments/catalog.py`, tem 7 entradas:

| canonical_id | catalog_status | coverage_tier | data_support_status |
| --- | --- | --- | --- |
| `equity.br.b3.petr4` | ACTIVE | P0_OPERATIONAL | PROVIDER_PENDING |
| `equity.us.nasdaq.aapl` | ACTIVE | P0_OPERATIONAL | PROVIDER_PENDING |
| `fii.br.b3.mxrf11` | CANDIDATE | P0_CATALOG | LICENSE_PENDING |
| `crypto.global.btc-usd` | CANDIDATE | FUTURE_REVIEW | METADATA_ONLY |
| `bdr.br.b3.aapl34` | CANDIDATE | FUTURE_REVIEW | METADATA_ONLY |
| `equity.br.b3.vale3` | CANDIDATE | FUTURE_REVIEW | METADATA_ONLY |
| `equity.br.b3.cmin3` | CANDIDATE | FUTURE_REVIEW | METADATA_ONLY |

VALE3 e CMIN3 entraram no Dia 41 por pedido do usuário, somente com metadados
([ADR-023](../adr/023-markets-hub-chart-type-and-motion.md)). CMIN3 (CSN Mineração ON)
não estava nos exemplos da tabela acima. Os benchmarks (IBOV, IFIX, S&P 500, NASDAQ, CDI,
IPCA e USD/BRL) não são instrumentos do catálogo: vêm de `/market-data/benchmarks`,
sintéticos e `DEMO`. Importar o restante exige decisão e o gate de licença por provider.

Fundos tradicionais permanecem P1 condicionado a fonte licenciada. A API e o frontend devem exibir o nível de suporte e nunca transformar `METADATA_ONLY` em cotação.
