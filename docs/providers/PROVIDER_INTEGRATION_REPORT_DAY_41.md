# Relatório de integração de providers (Dia 41)

- **Data:** 2026-10-11.
- **Branch:** `feature/dia-41-sync`; o SHA aparece no commit que traz este relatório.
- **Decisão:** [ADR-025](../adr/025-provider-registry-and-lifecycle.md).
- **Classificação:** arquitetura preparada, providers ainda não ativados.
- **Este documento não ativa provider nem autoriza deploy.**

## Atualização de 2026-10-12: ativação no staging privado

- **Decisão:** [ADR-027](../adr/027-owner-private-real-data-staging.md), por pedido explícito do
  responsável. A licença das respostas é `OWNER_APPROVED_PRIVATE_STAGING`, não
  `PUBLIC_APPROVED`, e só a sessão do responsável recebe dado real.
- **Código:**
  - o gateway fica em `app/market_data/live_data.py`;
  - os contratos são montados em `app/market_data/real_market_data.py`;
  - o registro e os normalizadores continuam os da ADR-025.
- **Chamadas reais medidas localmente**, com as chaves do `.env`: uma por endpoint, sem laço
  (`MARKET_PULSE_LIVE_PROVIDER_TESTS=1`, `tests/test_live_providers_optin.py`).

  | Provider | Endpoint | Resultado |
  | --- | --- | --- |
  | brapi | cotação PETR4 e `^BVSP` | OK |
  | brapi | histórico PETR4 com `includeRaw` | OK |
  | brapi | histórico `^BVSP` | 403, fora do plano: fica `LICENSE_BLOCKED` |
  | Twelve Data | `quote` e `time_series` AAPL (`adjust=none`) | OK |
  | Alpha Vantage | `GLOBAL_QUOTE` AAPL | OK |
  | Open Exchange Rates | `latest` USD/BRL | OK |
  | Massive | barras diárias AAPL, sem ajuste | OK |

- **Pelo gateway completo:**
  - PETR4 pela brapi (`DELAYED`);
  - AAPL pela Twelve Data, só com a data do pregão;
  - séries de 3 meses das duas;
  - Ibovespa pela brapi e USD/BRL pela Open Exchange Rates;
  - a segunda consulta saiu do cache.
- **Ainda indisponível, com motivo:**
  - histórico do Ibovespa;
  - cripto;
  - S&P 500, Nasdaq, CDI, IPCA e IFIX;
  - proventos e desdobramentos reais;
  - câmbio por Twelve Data ou Alpha Vantage, sem normalizador verificado.

## 1. Estado atual do projeto

- **Remoto:** staging em `fa6a95c`, com Vercel e Render alinhados e validados sem login.
  O código deste relatório está só na branch de trabalho.
- **Contratos públicos:** sem mudança; o OpenAPI ganhou só o acréscimo administrativo da
  seção 11.
- **CI:** não executa por bloqueio de cobrança (H-05).

## 2. Providers encontrados

Os sete candidatos já existiam no código: brapi, HG Brasil, Twelve Data, Alpha Vantage,
Open Exchange Rates, Massive e B3 for Developers. O único provider em uso é o `demo`, que
é sintético e serve só local e teste. Nenhum outro aparece no código ou no NotebookLM.

## 3. Capacidades de cada provider

Ficam no registro e na [matriz de onboarding](PROVIDER_ONBOARDING_MATRIX.md), com o que
foi confirmado e o que a fonte não declara. Resumo:

| Provider | Mercados | Capacidades |
| --- | --- | --- |
| brapi | BR | cotação, histórico, dividendos |
| HG Brasil | BR | cotação, câmbio |
| Twelve Data | global | cotação, histórico, câmbio |
| Alpha Vantage | global | cotação EOD, histórico, câmbio, eventos |
| Open Exchange Rates | câmbio | câmbio |
| Massive | EUA | cotação, histórico, dividendos, eventos |
| B3 for Developers | BR | nenhuma de mercado |

## 4. Status de licença

Todos estão `UNREVIEWED`. Nenhum dataset é `PUBLIC_APPROVED`. Os termos de uso não foram
lidos por inteiro nem aceitos.

## 5. Status de configuração

Nenhuma credencial foi cadastrada pelo agente. O painel interno mostra só "presente" ou
"ausente". Classificação por provider:

| Provider | Estado |
| --- | --- |
| brapi, Twelve Data, Alpha Vantage, Open Exchange Rates, Massive | preparado, aguardando chave e licença |
| HG Brasil | aguardando documentação do horário da fonte |
| B3 for Developers | bloqueado |

## 6. Variáveis necessárias

Os nomes estão no `.env.example`, com valores vazios: `BRAPI_API_TOKEN`,
`HG_BRASIL_API_KEY`, `TWELVE_DATA_API_KEY`, `ALPHA_VANTAGE_API_KEY`,
`OPEN_EXCHANGE_RATES_APP_ID`, `MASSIVE_API_KEY`, `B3_DEVELOPERS_CLIENT_ID`,
`B3_DEVELOPERS_CLIENT_SECRET` e `B3_DEVELOPERS_TOKEN_URL`.

Todas são opcionais e só do backend. Mantive os nomes existentes em vez dos sugeridos no
prompt (`BRAPI_API_KEY`, `B3_API_KEY`), para não quebrar o padrão.

## 7. Endpoints e contratos

- **Endpoints externos:** registrados por provider, com o método e o caminho documentados.
- **API pública:** sem mudança.
- **Contrato administrativo:** `/api/v1/admin/system` ganhou
  `providers.registry[]` (`AdminProviderRegistryItem`).

## 8. Modelo canônico

- `CanonicalQuote` e `CanonicalFxRate`; as barras usam `MarketBar`.
- Valores em `Decimal` e timestamps em UTC, com fuso obrigatório.
- Campos de proveniência: `canonical_id`, `provider`, `dataset`, `source_timestamp`,
  `session_date`, `ingested_at`, `data_level`, `is_demo`, `adjustment_type`,
  `quality_status`, `license_status` e `request_id`.
- `ValueUnit` (`PRICE`, `FX_RATE`, `INDEX_POINTS`, `UNDECLARED`) prepara o H-30.

## 9. Normalização

Os normalizadores de brapi, Twelve Data, Alpha Vantage, Open Exchange Rates e Massive
detectam:
- campo ausente e número em float;
- data sem fuso ou no futuro;
- moeda divergente, que vai para quarentena;
- ticker renomeado, também em quarentena;
- OHLC inconsistente e volume negativo;
- série ajustada quando se pediu não ajustada;
- série paginada, marcada como parcial.

A qualidade de série acusa duplicata, ordem, futuro e mistura de instrumento, moeda e
ajuste.

## 10. Precedência e fallback

- A precedência é uma proposta por capacidade e mercado.
- Só providers ativos entram na cadeia.
- Uma resposta vem de um único provider, sem misturar séries.
- O rastro registra o primário, quem serviu, as tentativas e o motivo.
- A ordem exige aprovação humana.

## 11. Cache e TTL

O cache existente foi reaproveitado:
- `CacheAsideService` em Redis, com envelope `stale_until`;
- cache negativo de 90 s;
- lock distribuído contra rajadas de recálculo;
- TTL por `DataLevel` em `freshness.py`.

| Nível | Cotação | Histórico |
| --- | --- | --- |
| Tempo real | 60 s, até 300 s | — |
| Atrasado | 900 s, até 7.200 s | — |
| EOD | 1 dia, até 7 dias | 1 dia, até 30 dias |

Indisponível fica 30 s no cache. Quando um provider entrar, o TTL tem de respeitar a
frequência do plano dele, por exemplo 30 min no gratuito da brapi.

## 12. Rate limits

| Provider | Limite documentado |
| --- | --- |
| brapi | 15k a 500k req/mês |
| Twelve Data | 8 créditos/min e 800/dia |
| Alpha Vantage | 25 req/dia |
| Open Exchange Rates | 1.000 req/mês no Free |
| Massive | 5 chamadas/min no Basic |

O transporte respeita o `Retry-After` (até 1 h), e há backoff com jitter e circuit
breaker. A cota mensal por provider ainda não tem contador: entra junto com a ativação.

## 13. Banco e Redis

Nenhuma migration. O schema já tem `providers`, `datasets`,
`provider_dataset_licenses`, `ingestion_runs`, `ingestion_batches`,
`raw_payload_records`, `quotes`, `price_bars`, `fx_rates` e as tabelas de quarentena.
`price_bars.volume` aceita nulo, o que permite gravar volume ausente sem inventar zero.

## 14. Alterações no backend

- **Módulos novos:** `registry.py`, `canonical.py`, `vendors.py`, `http.py`,
  `precedence.py` e `market_data/quality.py`.
- **Resiliência:** `Retry-After`, backoff e circuit breaker.
- **Correção de integridade:** `MarketBar` não preenche mais volume ausente com zero, e o
  DEMO diário segue a mesma regra.
- **Painel interno:** mostra o registro.

## 15. Alterações no frontend

- `src/lib/unavailable-reasons.ts` explica cada motivo em português e mantém o código.
- Usado na tela de mercados, na proveniência do ativo, nos proventos e no painel interno.
- O painel interno ganhou a tabela do registro.

## 16. Alterações no catálogo

Nenhuma nova: a separação entre catálogo planejado e operacional já foi feita no H-31.

## 17. Testes

- **Novos no backend (31):** registro, ciclo de vida, ativação, credenciais, precedência,
  `Retry-After`, circuit breaker, normalizadores por provider, transporte, redação de
  URL, qualidade de série e volume ausente.
- **Novos no frontend (2):** motivos explicados e tabela do registro.
- **Integração com API real:** nenhum teste; continua opt-in e fora do padrão.

## 18. Design

Os elementos das referências que dependem de dados estão na seção "Dados e providers"
da [matriz de design](../design/DESIGN_REFERENCE_MATRIX_DAY_41.md).

## 19. Migrations

Nenhuma.

## 20. Riscos de licença

- **Exibição a usuários:** o Basic da Twelve Data é "non-display" e os planos da Massive
  são "Individual use".
- **Uso comercial:** a brapi indica planos pagos para produção.
- **Cache e redistribuição:** a Open Exchange Rates não declara a regra na página lida.

Nada pode ser exibido no produto sem revisão jurídica dos termos.

## 21. Riscos de custo

Os planos gratuitos não sustentam um produto público: 25 req/dia, 5 por minuto e 1.000
por mês. Qualquer uso real exige plano pago, decisão que é do usuário.

## 22. Riscos de performance

O refresh sem cota estoura os limites, e a API grátis do Render hiberna (H-27). O refresh
precisa de lote, cache e cron controlados (H-05 e decisão C4).

## 23. Riscos de segurança

- As chaves ficam só no backend e nunca entram na URL de mensagens.
- O painel mostra apenas a presença das chaves.
- O transporte recusa o envio sem ativação.

## 24. O que pode ser implementado agora

Contadores de cota por provider em Redis, o job de refresh por provider em modo
`DRY_RUN` e testes de contrato com mais fixtures documentadas.

## 25. O que depende de chave

Testes de integração opt-in e a medição de latência real.

## 26. O que depende de contrato ou licença

Qualquer exibição pública, a B3 for Developers, dados de fundos e de renda fixa, e
indicadores.

## 27. O que depende de decisão humana

- A ordem de precedência.
- Quais planos contratar.
- A tolerância de divergência entre fontes.
- A unidade dos benchmarks (ADR-024).

## 28. Plano de implementação

1. Revisão jurídica dos termos de um provider por vez, começando por câmbio (Open
   Exchange Rates) e B3 (brapi).
2. `CONFIGURED`: chave no painel do Render.
3. `INTEGRATION_TESTED`: teste opt-in com poucas chamadas.
4. `LICENSE_REVIEW_PENDING`, depois `APPROVED`, depois `ACTIVE`, por pull request.
5. Persistência e refresh do provider aprovado.

## 29. Plano de deploy

Este código não muda a API pública nem exige migration. Ele pode ir ao staging no mesmo
SHA da Vercel e do Render, quando o usuário autorizar a promoção: push para
`feature/dia-29-staging`, deploy manual no Render (H-33) e Redeploy na Vercel se a leitura
do Git falhar.

## 30. Plano de rollback

- **Banco:** nada muda.
- **Remoto:** voltar Vercel e Render ao deployment de `fa6a95c`.
- **Código:** se for preciso, reverter os commits do registro, que não têm efeito em dados
  porque nenhum provider está ativo.
