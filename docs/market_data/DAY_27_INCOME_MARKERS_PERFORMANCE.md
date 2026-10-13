# Dia 27 — Proventos, eventos no gráfico e hardening

## Escopo executado

O gate opt-in `apps/api/tests/test_day27_integrated_gates.py` reconstitui o
cenário no banco dedicado `market_pulse_demo`, carrega todos os marcadores de
uma carteira DEMO pelo serviço PostgreSQL real e confere cada `source_id` contra
a linha persistida correspondente. O teste exige pelo menos uma origem de
ledger e uma de ação corporativa; nenhum marcador decorativo ou não ancorado é
aceito.

O Dia 27 expõe projeções factuais e somente leitura de proventos, JCP, splits e
grupamentos para uma carteira do usuário em `GET /api/v1/portfolios/{id}/income`.
Marcadores de gráfico são servidos por `GET /api/v1/portfolios/{id}/event-markers`.
Cada marcador contém `source_type` e `source_id` de uma linha real de
`portfolio_events` ou de uma ação corporativa homologada; a validação rejeita
qualquer referência órfã antes da resposta.

Valores monetários e razões permanecem `Decimal`/strings no contrato. Nenhum
cálculo de patrimônio, P&L ou rentabilidade foi alterado. A interface oferece
tabela HTML equivalente ao gráfico, com estado de fonte, `DataLevel` e
`Freshness` visíveis.

## Telemetria e privacidade

O mesmo gate integrado envia LCP, INP e CLS ao endpoint real e audita
`web_vital_metrics` diretamente no PostgreSQL DEMO. Além do `id` técnico, a
tabela só pode conter `route`, `metric`, `bucket_start`, `value_sum`,
`sample_count` e `updated_at`; as linhas são verificadas contra fragmentos de
PII reconhecíveis. O workflow `demo-integration.yml` executa esse gate com as
demais validações persistidas.

`POST /api/v1/telemetry/web-vitals` aceita somente LCP, INP e CLS, rota e
amostra agregada. A API rejeita chaves ou valores que pareçam PII e persiste
apenas soma, quantidade e bucket diário; URL completa, cookie, IP, e-mail e
payload bruto não são armazenados.

## Orçamento de performance

O gate `scripts/day27_performance_gate.mjs` valida P95 máximo de LCP 2.500 ms,
INP 200 ms e CLS 0,10 para as rotas P0. O mesmo gate inspeciona o bundle P0
gerado e falha se encontrar dependências/tokens de Three.js, Babylon ou WebGL.
O workflow `.github/workflows/day27-compliance.yml` executa lint, typecheck,
testes, build, orçamento e o smoke test Axe/Playwright.

As métricas do arquivo `apps/web/performance/day27-fixtures.json` são fixtures
determinísticas para o gate local; telemetria de produção futura deve continuar
agregada e sem PII antes de substituir as fixtures.

## Acessibilidade e decisão de gráficos

As rotas de terminal, carteiras, comparação e calendário passam por Axe em
Playwright. O Particle Atlas continua SVG/HTML acessível, com fallback tabular.
TradingView Lightweight Charts fica adiado: somente poderá ser avaliado quando
Decimal, `DataLevel`, `Freshness` e proveniência puderem ser preservados sem
conversão implícita para `float`. WebGL/3D permanece P1 e não entra no bundle
crítico do beta.

## Limitações

Os dados do ambiente local de demonstração são `DEMO` e fictícios. Não há
provider financeiro real, scraping, recomendação de investimento ou autorização
de redistribuição de dados neste dia.
