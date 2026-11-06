# ADR-024: Unidade dos benchmarks (decisão pendente)

- Status: **Proposed**. Aguarda decisão do responsável e um provider aprovado.
- Data: 2026-10-11
- Relação: [ADR-023](023-markets-hub-chart-type-and-motion.md), H-30 no
  [handoff](../DAY29_HANDOFF.md)

## Contexto

`BenchmarkItem` traz `value` e `currency`, mas não diz o que o valor mede. Os sete
benchmarks (IBOV, IFIX, S&P 500, NASDAQ, CDI, IPCA e USD/BRL) são níveis sintéticos `DEMO`
(`apps/api/app/market_data/benchmarks.py`), sem provider.

Procurei a unidade no contrato, na especificação, na documentação do Dia 26 e na
semântica de gráficos: nenhuma fonte a define. Na prática:

- CDI pode ser taxa ao ano ou fator diário;
- IPCA pode ser variação mensal, variação em 12 meses ou número-índice;
- IBOV e IFIX são pontos;
- USD/BRL é cotação.

Para os valores sintéticos, nenhuma dessas leituras é verdadeira nem falsa: o número não
mede nada. Até o Dia 41, a tela mostrava `10.50 BRL` para o CDI, o que sugeria uma unidade
que o contrato não declara.

## Feito agora, sem decidir a unidade

- A API acrescenta às limitações de cada benchmark a frase "Unidade não declarada…". O
  schema não muda.
- A tela de mercados mostra "unidade não declarada" no lugar da moeda e explica isso na
  nota das abas com benchmarks.

## Opções para a decisão

| Opção | O que muda | Prós | Contras |
| --- | --- | --- | --- |
| A. Campo `unit` no contrato (`PERCENT_PER_YEAR`, `PERCENT_MONTH`, `PERCENT_12M`, `INDEX_POINTS`, `INDEX_NUMBER`, `QUOTE`, `UNDECLARED`), preenchido só com metadado do provider | Nova versão do OpenAPI e do cliente gerado | Unidade explícita e testável; `UNDECLARED` até haver fonte | Exige definir a lista com o provider; muda o contrato |
| B. Tirar `value` da lista de benchmarks até haver provider | Remove o número sintético da lista | Nenhuma leitura errada possível | Perde a demonstração; o gráfico em INDEX_100 continua |
| C. Manter como está (valor e limitação em texto) | Nada | Já feito; zero risco de contrato | A unidade continua só em texto |

**Recomendação:** C até existir provider aprovado; A junto com o gate de licença desse
provider. A opção B só se o responsável preferir não mostrar números sintéticos na lista.

## Consequências

Nenhuma unidade é publicada sem fonte. Quando o provider entrar, a escolha da opção A vira
nova ADR (Accepted), com a fonte oficial de cada unidade registrada.
