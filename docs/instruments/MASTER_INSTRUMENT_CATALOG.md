# MASTER_INSTRUMENT_CATALOG

> **Dois catálogos, conferidos em 2026-10-11 (H-31).**
>
> - **Operacional:** o que a API serve, em `apps/api/app/instruments/catalog.py`. Tem
>   **7 entradas**, listadas em "Catálogo operacional" abaixo.
> - **Planejado:** a lista de referência do Dia 8, com 727 linhas. **Não foi importada**:
>   nenhuma linha dela existe na API nem na interface.
>
> Importar o planejado exige fonte confiável, decisão do usuário e testes de identidade.
> Até lá, nenhum número deste documento descreve o produto em funcionamento.

## Catálogo planejado (referência do Dia 8, não importado)

Catálogo estático amplo, normalizado a partir da lista inicial fornecida para o Dia 8. A lista de referência tinha 727 linhas de instrumentos; duplicatas seriam tratadas por categoria e símbolo. Nenhum registro contém preço, volume, variação ou histórico.

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

## Catálogo operacional (código, conferido em 2026-10-11)

`MASTER_CATALOG`, em `apps/api/app/instruments/catalog.py`, tem 7 entradas:

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

### Como cada estado aparece

| Estado | Campos do contrato | O que a interface mostra |
| --- | --- | --- |
| Disponível com dado aprovado | `data_support_status=DATA_AVAILABLE_APPROVED` | Nenhum hoje: nenhum provider passou no gate de licença |
| Operacional com dado sintético | `support_state=P0_OPERATIONAL`, cotação `data_level=DEMO` | Valor com selo DEMO (PETR4, AAPL) |
| Candidato só com metadados | `support_state=CANDIDATE_FUTURE`, `METADATA_ONLY` | "Indisponível" e "Candidato · só metadados" |
| Bloqueado por licença | `LICENSE_PENDING` | "Indisponível" e "licença pendente" (MXRF11) |
| Sem cotação | Cotação `freshness=UNAVAILABLE` com `unavailable_reason` | "Indisponível" e o motivo |
| DEMO local | Catálogo do Dia 24 (`exchange=DEMO`), só com DEMO ligado | Nomes fictícios com selo DEMO |
| Fora do escopo | `catalog_status=OUT_OF_SCOPE` (`support_state=BLOCKED_SCOPE`) | Nenhum hoje; `MUTUAL_FUND` só pode existir assim |

O teste `test_no_catalog_entry_is_priced_without_an_approved_dataset` garante duas coisas:
nenhuma entrada fora do universo operacional recebe preço, e o preço do universo
operacional é sempre `DEMO`.

Fundos tradicionais permanecem P1 condicionado a fonte licenciada. A API e o frontend devem exibir o nível de suporte e nunca transformar `METADATA_ONLY` em cotação.
