# Matriz de onboarding de providers financeiros

Status: pesquisa técnica inicial, nenhum provider aprovado (`UNREVIEWED`). Revisada em 2026-08-31.

## Resumo executivo

O Market Pulse mantém o frontend isolado de qualquer provider: `apps/web` usa o cliente TypeScript gerado, chama `/api/v1`, e somente o gateway interno pode selecionar adapters. Esta matriz registra candidatos e hipóteses verificáveis; não concede licença, não ativa integração e não presume que plano gratuito/teste permita uso comercial ou redistribuição.

## Regra default deny

Cada combinação de provider, plano, endpoint, dataset, finalidade e modalidade começa `UNREVIEWED`. Ausência de evidência, sandbox/demo, acesso interno ou feature flag bloqueia publicação. Apenas `PUBLIC_APPROVED` com evidência contratual vigente pode alimentar API pública.

## Tabela comparativa

| Provider | API/protocolo | Autenticação | Cobertura candidata | Limites/preço publicados | Prioridade | Status |
| --- | --- | --- | --- | --- | --- | --- |
| [brapi](https://brapi.dev/docs) | REST/JSON; SDKs TS/Python | Bearer token; sandbox limitado sem token | Ações B3, índices, ETFs/FIIs conforme endpoint, histórico, dividendos | Gratuito anunciado: 15k/mês, 1 ticker/chamada, ~30 min; planos pagos variam | P0 candidato Brasil | `UNREVIEWED` |
| [HG Brasil](https://hgbrasil.com/docs/guide/key) | REST/JSON | API key (`key`); chave interna recomendada | B3, índices, FX; dividendos dependem do plano | Limites variam por plano; valores e redistribuição pendentes | P1 backup Brasil | `UNREVIEWED` |
| [Twelve Data](https://twelvedata.com/docs/introduction/quickstart) | REST/JSON e WebSocket | API key | Ações, ETFs, fundos, FX, commodities e histórico | Basic grátis: 8 créditos/min e 800/dia; planos exibem créditos e uso individual | P1/P2 global | `UNREVIEWED` |
| [Alpha Vantage](https://www.alphavantage.co/support/) | REST/JSON/CSV | API key | Ações, ETFs, FX, histórico e indicadores | Gratuito: 25 req/dia; realtime/15-min US é premium/licenciado | P1/P2 alternativo | `UNREVIEWED` |
| [Open Exchange Rates](https://docs.openexchangerates.org/reference/authentication) | REST/JSON | `app_id` ou `Authorization: Token` | FX e séries históricas | Free anunciado: 1.000 req/mês, atualização horária, base USD | P0 candidato FX | `UNREVIEWED` |
| [Massive/Polygon](https://massive.com/docs) | REST/JSON, WebSocket, flat files | API key/Bearer conforme produto | Ações/ETFs, índices, FX, corporate actions e histórico | Free anunciado: 5 req/min; redistribuição/customer-facing exige plano Business | P2 premium | `UNREVIEWED` |
| [B3 for Developers](https://developers.b3.com.br/apis) | REST/JSON | OAuth2/client credentials e mTLS conforme API | APIs oficiais B3 sob contrato | Licença, certificados e limites dependem do produto contratado | P3 institucional | `UNREVIEWED` |

Fundos tradicionais permanecem condicionados a cobertura e licença explícitas. Nenhum item acima está autorizado para produção.

## Matriz de capabilities

| Provider | Latest quote | Histórico | FX | Metadados | Dividendos/JCP | Splits/corporate actions | ETFs | FIIs | Fundos tradicionais |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| brapi | provável | provável | não objetivo | provável | endpoint a confirmar | a confirmar | a confirmar | a confirmar | não confirmado |
| HG Brasil | provável | a confirmar | provável | a confirmar | plano a confirmar | não confirmado | não confirmado | não confirmado | não confirmado |
| Twelve Data | sim | sim | sim | sim | a confirmar | a confirmar | sim | não confirmado | sim conforme plano |
| Alpha Vantage | sim | sim | sim | sim | não confirmado | não confirmado | sim | não confirmado | não confirmado |
| Open Exchange Rates | não | FX histórico | sim | não | não | não | não | não | não |
| Massive/Polygon | sim | sim | sim | sim | sim | sim | sim | não | não confirmado |
| B3 for Developers | contrato | contrato | contrato | contrato | contrato | contrato | contrato | contrato | contrato |

“Sim” indica capability técnica documentada, não permissão de uso público.

## Matriz de variáveis de ambiente

| Provider | Variável | Exposição | Estado inicial |
| --- | --- | --- | --- |
| brapi | `BRAPI_API_TOKEN` | somente backend | vazia/desabilitada |
| HG Brasil | `HG_BRASIL_API_KEY` | somente backend | vazia/desabilitada |
| Twelve Data | `TWELVE_DATA_API_KEY` | somente backend | vazia/desabilitada |
| Alpha Vantage | `ALPHA_VANTAGE_API_KEY` | somente backend | vazia/desabilitada |
| Open Exchange Rates | `OPEN_EXCHANGE_RATES_APP_ID` | somente backend | vazia/desabilitada |
| Massive | `MASSIVE_API_KEY` | somente backend | vazia/desabilitada |
| B3 | `B3_DEVELOPERS_CLIENT_ID`, `B3_DEVELOPERS_CLIENT_SECRET`, `B3_DEVELOPERS_TOKEN_URL` | somente backend | vazias/desabilitadas |

Nenhuma variável usa prefixo público. Segredos devem ser `SecretStr`/secret manager em ambientes autorizados e nunca aparecer em repr, log, erro ou navegador.

## Endpoints candidatos

| Provider | Endpoints/documentação candidata | Uso futuro |
| --- | --- | --- |
| brapi | `/api/v2/stocks/quote`, histórico e dividendos conforme OpenAPI | Brasil P0 após licença |
| HG Brasil | `https://api.hgbrasil.com/finance` e recursos documentados | backup Brasil/FX |
| Twelve Data | `/price`, `/time_series`, WebSocket quotes | EUA/ETFs/FX |
| Alpha Vantage | `GLOBAL_QUOTE`, `TIME_SERIES_DAILY`, `FX_*` | alternativa global |
| Open Exchange Rates | `/latest.json`, `/historical/*.json`, `/time-series.json` | USD/BRL |
| Massive | REST aggregates/trades/quotes e WebSocket | premium EUA |
| B3 | catálogo em `developers.b3.com.br` | integração institucional |

Endpoints são apenas referências; cada combinação requer revisão contratual e teste sem dados reais.

## Plano de ativação futura

1. Revisar termos, plano, dataset, cobertura, cache, display e redistribuição.
2. Registrar provider/dataset no banco como `UNREVIEWED`.
3. Guardar credencial no ambiente seguro, nunca no repositório.
4. Testar adapter sem rede em local e com sandbox autorizado em staging.
5. Validar timeout, rate limit, fallback, proveniência, logs e freshness.
6. Obter aprovação humana e alterar para `PUBLIC_APPROVED` somente para o escopo exato.
7. Atualizar OpenAPI/cliente somente se o contrato público mudar.

## Checklist de licença e segurança

- [ ] Termos e política comercial oficiais revisados.
- [ ] Plano, endpoint, dataset, finalidade e modalidade registrados.
- [ ] Exibição pública e redistribuição autorizadas explicitamente.
- [ ] Delay, retenção, cache, atribuição, região e quotas registrados.
- [ ] Segredo armazenado fora do código e nunca enviado ao frontend.
- [ ] Adapter desabilitado sem configuração e sem rede por padrão.
- [ ] Logs, erros e métricas não revelam credenciais ou payloads sensíveis.
- [ ] Proveniência e `FRESHNESS` testados, incluindo fallback `STALE`.
- [ ] Aprovação humana registrada; nunca automática.

## Consumo indireto pelo frontend

O fluxo é `web → cliente gerado → /api/v1 → catálogo/gateway → licensing service → adapter`. O frontend recebe apenas resposta normalizada com fonte, horário, `DataLevel`, `Freshness`, moeda e limitações. Sem aprovação, a API entrega `DEMO`, `UNAVAILABLE` ou Problem Details seguro; nenhuma chave chega ao navegador.

## Riscos e decisões pendentes

- Licenças de display/redistribuição e uso comercial ainda não foram confirmadas.
- Cobertura de FIIs, JCP, fundos tradicionais e corporate actions precisa de evidência por dataset.
- Rate limits e preços podem mudar; revisar antes de qualquer contratação.
- B3 pode exigir mTLS, certificados e contrato institucional.
- Massive/Polygon mudou de marca; endpoints antigos e termos devem ser reconciliados.
- Decidir provider P0 somente após matriz preenchida e aprovação documental.
