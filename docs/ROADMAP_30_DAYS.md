# Market Pulse — roadmap canônico de 30 dias

- **Status:** Aprovado para execução diária mediante autorização
- **Data-base:** 2026-08-30
- **Premissa:** 30 dias corridos, uma pessoa com uso intensivo do Codex
- **Regra:** cada dia termina em seu próprio gate e não autoriza o dia seguinte

## Prioridades do beta

- **P0 — bloqueia o beta:** fundação, API, persistência, resiliência, autenticação, busca/páginas de ativos aprovados, dashboard, Particle Atlas básico e acessível, Global Atlas tabular, heatmap básico, watchlist, carteiras informativas, performance factual, Morning Call, segurança, testes e artefatos de deploy.
- **P1 — condicional:** fundos tradicionais licenciados, heatmap avançado, partículas, ondas, transições avançadas, Canvas/WebGL, profundidade e globo 3D leve. Só entra após P0 verde, com feature flag, fallback e movimento reduzido.
- **Pós-beta:** notificações, IA, recomendação, mobile, alta escala, integrações não essenciais e cobrança real.

Stripe é exceção limitada: no beta, somente integração em modo de teste, sem cobrança real, contratação ou publicação. Sua ausência não pode comprometer o fluxo informativo principal.

## Semana 1 — fundação e contratos

| Dia | Objetivo e entregáveis | Dependências | Gate objetivo |
| --- | --- | --- | --- |
| 1 | Canonizar spec, roadmap, arquitetura, políticas, plano técnico, governança, CODEOWNERS, template e CI documental; criar dois commits locais | Repositório isolado | Árvore limpa; documentos canônicos não vazios; auditorias de escopo, segredos e código verdes; nenhum produto/deploy |
| 2 | Scaffold mínimo `apps/web` (Next.js App Router, TypeScript strict, Tailwind) e `apps/api` (FastAPI); lockfiles | Dia 1 aprovado | Ambos iniciam localmente; lint/typecheck/testes mínimos passam; sem domínio financeiro |
| 3 | Dockerfiles e Compose apenas local para web/API/PostgreSQL/Redis | Dia 2 | Healthchecks verdes; volumes e rede documentados; nenhum serviço externo criado |
| 4 | SQLAlchemy 2, Alembic e primeira migração | Dia 3 | Upgrade/downgrade em banco vazio reproduzíveis |
| 5 | `/api/v1`, health, Problem Details e OpenAPI | Dia 4 | Contract tests e schema passam; erros não vazam detalhes |
| 6 | Interface de provider, adapter fake, fixtures sintéticas e license gate | Dia 5 e matriz | Dataset sem `PUBLIC_APPROVED` não chega a resposta pública |
| 7 | Gate semanal e CI executável de aplicação | Dias 2–6 | Build/lint/typecheck/testes rodam por comandos documentados e sem rede real |

**Entregável semanal:** fundação executável local, contrato HTTP, migração e fronteira de provider demonstrável sem dado real.

## Semana 2 — dados e resiliência

| Dia | Objetivo e entregáveis | Dependências | Gate objetivo |
| --- | --- | --- | --- |
| 8 | Catálogo mestre, universo P0 e backlog de candidatos, com status explícito | Dia 7 | Catálogo amplo não implica suporte de dados; `canonical_id` e default deny documentados |
| 9 | Adapters candidatos, normalização inicial e payload bruto sanitizado | Dia 8 ou fixtures | Adapters não expõem payload externo; fixtures determinísticas e sem rede real |
| 10 | Normalizar OHLC/FX, ajustes, upsert e quarentena | Dia 9 | Decimal, invariantes, provenance e quarentena cobrem payloads inválidos |
| 10.1 | Integridade financeira e separação de DataLevel/Freshness | Dia 10 | Política, contratos e testes bloqueiam floats, timestamps ingênuos e proveniência incompleta |
| 11 | Pipeline de eventos corporativos: dividendos, JCP, splits, grupamentos e reconciliação auditável | Dia 10 | Eventos normalizados com Decimal, status controlado, idempotência externa, versionamento, correção/cancelamento e quarentena; nenhum crédito automático em carteira |
| 11.1 | Reconciliação documental do roadmap com eventos corporativos executados | Dia 11 | Histórico preservado e refresh idempotente realocado para Dia 12.1 |
| 12 | Cache-aside, freshness, stale-if-error, negative cache, invalidação granular e locks | Dias 9–11 | Clock tests provam `FRESH`, `STALE` e `UNAVAILABLE`; stale nunca é silencioso |
| 12.1 | Reconciliação estrutural e refresh interno idempotente | Dia 12 e contratos de ingestão | Gaps de identidade/provenance/licença corrigidos; repetição não duplica; lock e invalidação granular funcionam |
| 13 | API de catálogo, busca, páginas de ativo, quotes, histórico, variação e eventos permitidos | Dias 8–12.1 | Resposta parcial mistura estados corretamente e preserva proveniência; ativos sem licença permanecem bloqueados |
| 13 | Serviço `refresh_market_data` e endpoint interno protegido `POST /api/v1/internal/refresh-quotes` | Dia 12.1 | Segredo `X-Cron-Secret`, comparação em tempo constante, limites, lock, idempotência, falhas parciais e DEMO seguro; nenhum provider real |
| 14 | Automação operacional: workflow agendado/manual, backfill controlado, reconciliação diária e gate da Semana 2 | Dia 13 e contratos de ingestão | Cron/manual usa apenas secrets; backfill limitado, idempotente e default-deny; gaps, provenance e falhas parciais são auditáveis |

**Entregável semanal:** API financeira normalizada, resiliente e bloqueada por licença, com fallback observável e sem alegação indevida de tempo real.

### Adendo operacional do Dia 14

O Dia 14 executado corresponde à automação operacional de mercado: workflow
agendado/manual, backfill controlado, reconciliação diária e fechamento do
gate da Semana 2. O registro anterior de agregação do heatmap permanece como
histórico e permanece explicitamente no Dia 17 junto à página de ativo; recursos
avançados de heatmap continuam P1.

## Semana 3 — produto e experiência

| Dia | Objetivo e entregáveis | Dependências | Gate objetivo |
| --- | --- | --- | --- |
| 15 | Market data público: catálogo, quotes e séries históricas consumíveis pelo frontend, com `DEMO`, `UNAVAILABLE`, provenance, `PRICE`, `INDEX_100`, fallback tabular, OpenAPI e cliente TypeScript | Contratos de dados e licenciamento | Endpoints públicos tipados preservam fonte, timestamps, estados e limitações; nenhum provider real ou dataset não aprovado |
| 16 | Shell frontend Particle Atlas: tema claro/escuro, app shell, layout do terminal, componentes de provenance/estado e consumo inicial do cliente TypeScript gerado | Market data público do Dia 15 | Shell responsivo e acessível; tokens monocromáticos, estados `DEMO`/`STALE`/`UNAVAILABLE` e metadados visíveis; sem tipos financeiros paralelos |
| 17 | Página de ativo, gráfico Particle Atlas, comparação, períodos, painel contextual e fallback tabular | Shell e contratos do Dia 16 | Uma série = uma linha; multissérie = `INDEX_100`; valores reais, provenance e tabela acessível preservados |
| 18 | Cadastro, login, logout e sessão opaca | Persistência | Argon2id, cookie `HttpOnly`, Origin/CSRF, expiração e revogação testados |
| 19 | Watchlist por usuário | Dia 18 | Isolamento horizontal; estados vazio/erro/stale; sem gestão ou recomendação |
| 20 | Carteiras informativas: múltiplas carteiras, moeda-base imutável, ledger manual append-only, caixa e posições | Dia 18 e schema financeiro | Replay determinístico com `Decimal`; isolamento horizontal; idempotência; reversão sem mutar evento original; sem valuation, P&L, TWR ou recomendação |
| 21 | Global Atlas P0 em tabela acessível e gate integrado de UX | Dias 15–20 | Fluxos principais por teclado; disclaimer e metadados visíveis; sem recomendação |

**Entregável semanal:** experiência P0 responsiva e acessível com dashboard, heatmap, Global Atlas tabular, sessão, watchlist e Morning Call.

### Adendo documental do Dia 20

O Dia 20 executado corresponde ao domínio de carteiras informativas e não ao
Morning Call descrito em versões anteriores deste quadro. O Morning Call não foi
apagado como requisito: permanece pendente para o próximo dia apropriado, antes
do Global Atlas. A reconciliação está registrada em
[DAY_20_ROADMAP_RECONCILIATION.md](engineering/DAY_20_ROADMAP_RECONCILIATION.md).

### Adendo documental do Dia 18.1

O Dia 18.1 reconcilia a diretriz visual Particle Atlas com o estado real após os
Dias 16–19. Shell, temas, gráfico SVG P0, autenticação, sessões, watchlists e
favoritos já existem; provider/dado real, carteiras, P&L e TWR ainda não. A
reconciliação é documental e não altera o escopo nem autoriza bibliotecas,
Canvas, WebGL, provider ou dados reais.

## Semana 4 — hardening e release candidate

| Dia | Objetivo e entregáveis | Dependências | Gate objetivo |
| --- | --- | --- | --- |
| 22 | Validador editorial e Morning Call factual: blocos tipados, fontes, estados, versionamento append-only e leitura pública | Dados e política de conteúdo canônica | Somente `PUBLISHED` é público; linguagem prescritiva é bloqueada; provenance editorial e fallback seguro passam |
| 23 | Integração compatível com Neon PostgreSQL e Upstash Redis REST | Stack local verde | Migração, TTL, lock, fallback e falha segura passam sem provisionar externamente |
| 24 | Testes frontend/a11y; P1 visual somente se orçamento permitir | UX P0 verde | Estados críticos cobertos; P1 feature-flagged, não bloqueante e com fallback |
| 25 | Painel operacional interno `/admin/system`: RBAC `ADMIN`, health, jobs, providers, quarentena, locks, editorial, volumetria e auditoria | Dia 24 e sessão HttpOnly | Contrato OpenAPI, request IDs, mascaramento, acesso ADMIN-only e estados degradados passam sem provider real |
| 26 | Comparação multiativo, benchmarks e calendário econômico: lotes de quotes/histórico, `PRICE`/`INDEX_100`, universo fixo DEMO e eventos factuais | Contratos públicos e OpenAPI | Máximo de 10 séries, `Decimal`, provenance/DataLevel/Freshness, gaps e fallback tabular, léxico sem recomendação, UI acessível e gates automatizados |
| 27 | Proventos, JCP, splits/grupamentos, marcadores referenciados no gráfico, telemetria Web Vitals agregada e hardening de UX/performance | Contratos de carteiras, eventos corporativos e Particle Atlas | Proventos preservam `Decimal`/provenance; marcadores apontam para ledger/ação real; PII é rejeitada; Axe e budgets P95 LCP/INP/CLS passam; sem 3D/WebGL no bundle P0 |
| 28 | Artefatos para Vercel (web) e Render (API), non-root e shutdown | Checks verdes | Smoke local equivalente passa; nenhum login/deploy externo |
| 29 | Preparar GitHub Actions agendado para chamar endpoint interno protegido | Refresh idempotente | Dry run/manual controlado; segredo não versionado; cold start/falha documentados |
| 30 | Release candidate e auditoria final | Todos os gates | Regressão, migração, a11y, segurança, licença, limitações e checklist evidenciados |

**Entregável semanal:** release candidate reproduzível e preparado para Vercel/Render/Neon/Upstash/GitHub Actions, sem provisionamento ou publicação não autorizados.

### Reconciliação autorizada do Dia 24

O prompt direto do Dia 24 define **seed DEMO oficial, reset reprodutível e E2E
principal**, incluindo isolamento entre usuários, coerência financeira e
correções mínimas dos gráficos e scanner de segredos. A linha histórica de
testes frontend/a11y e P1 visual acima é preservada, mas não autoriza expansão
visual nesta execução. O escopo de E2E antes planejado para o Dia 25 passa a
integrar este gate, sem declarar o Dia 25 executado.

O operador aprovou exclusivamente o banco local `market_pulse_demo`, com
múltiplas barreiras e preservação do banco principal e das proteções append-only.
O gate foi concluído localmente em 2026-09-07: migrations em banco DEMO vazio,
reset/seed repetidos com fingerprint lógico estável, health de PostgreSQL/Redis
e E2E principal e de isolamento A/B. Estado, comandos e limitações em
[DEMO_SEED_DAY_24.md](demo/DEMO_SEED_DAY_24.md). No momento desta reconciliação,
o Dia 25 ainda não estava executado.

### Execução autorizada do Dia 25

O Dia 25 foi replanejado e executado como painel operacional interno em
`/api/v1/admin/system` e `/admin/system`. O painel agrega somente diagnósticos
seguros: PostgreSQL, Redis, contrato OpenAPI, jobs, governança default-deny de
providers/datasets, quarentena, locks, consumo editorial e volumetria. O acesso
exige sessão válida e papel `ADMIN`; tentativas permitidas e rejeitadas são
registradas em `audit_logs` com `request_id`, sem credenciais, cookies, payloads
brutos ou PII. O runbook canônico está em
[ADMIN_SYSTEM_DAY_25.md](operations/ADMIN_SYSTEM_DAY_25.md). Nenhum provider
real, dado real, Stripe, corretora, IA ativa ou deploy foi ativado.

### Reconciliação autorizada do Dia 26

O Dia 26 foi executado como comparação multiativo, benchmarks e calendário
econômico, conforme o prompt direto aprovado. A implementação inclui contratos
em lote para quotes e histórico, normalização `INDEX_100` com `Decimal`,
benchmark fixo sintético `DEMO`, calendário factual com limite de 366 dias,
proveniência, timezone IANA, bloqueio lexical e telas Particle Atlas com tabela
acessível. A linha anterior de hardening de CORS/cookies/rate limit não é
apagada do histórico; permanece como trabalho de hardening a ser replanejado
depois deste gate. Detalhes e comandos estão em
[DAY_26_MULTIATIVE_CALENDAR.md](market_data/DAY_26_MULTIATIVE_CALENDAR.md).

### Reconciliação autorizada do Dia 28 (2026-10-01)

**Decidido pelo usuário em 2026-10-01.** O Dia 28 foi executado como hardening de
segurança, privacidade e operação: remoção do endpoint de ledger sem
autenticação, CSRF por Origin em todo método mutante, cabeçalhos de segurança,
validação estrita de configuração de produção, exclusão de conta por
anonimização com revogação de sessões e auditoria atômica, export com valores
decimais, backup/restore com verificação de integridade e expurgo de registros
operacionais com dry-run por padrão. Estado do dia: **FECHADO em 2026-10-01**, por decisão do usuário, com as rodadas locais executadas e informadas pelo responsável e as pendências transferidas ao Dia 29 (ver [DAY29_HANDOFF.md](DAY29_HANDOFF.md)).

A linha do Dia 28 da tabela acima, "Artefatos para Vercel (web) e Render (API),
non-root e shutdown", com o gate "Smoke local equivalente passa", **não é
apagada do histórico**. Por decisão do usuário nesta data, esses artefatos
(Dockerfiles non-root, shutdown gracioso e a confirmação de que Vercel e Render
exigem ou dispensam imagem) **saem do Dia 28 e passam ao Dia 29**, porque não são
validáveis sem um ambiente com memória suficiente para construir imagens e porque
o plano de deploy ainda precisa confirmar, na fonte oficial, se as plataformas
exigem imagem. O gate de smoke local equivalente fica, portanto, **não executado**
no Dia 28 e é herdado pelo Dia 29.

O Dia 29 passa a acumular o escopo da sua linha da tabela (GitHub Actions
agendado para o endpoint interno protegido) com as pendências transferidas, cada
uma com origem, motivo e critério de pronto, em
[DAY29_HANDOFF.md](DAY29_HANDOFF.md). Esta reconciliação não autoriza deploy,
login externo, contratação nem provisionamento. Decisões e evidências do Dia 28
estão em [PRODUCTION_RUNBOOK_DAY_28.md](operations/PRODUCTION_RUNBOOK_DAY_28.md).

### Reconciliação autorizada do Dia 29 (2026-10-01)

**Decidido pelo usuário em 2026-10-01**, registrando uma decisão anterior que não
havia sido gravada no repositório. O Dia 29 passa a ser **preparação e deploy de um
staging PRIVADO**, com acesso somente do usuário.

Divergências com o texto anterior, que **não é apagado do histórico**:

- a linha do Dia 29 da tabela ("Preparar GitHub Actions agendado para chamar
  endpoint interno protegido") deixa de ser o escopo inteiro do dia. O workflow
  agendado já existe (`.github/workflows/market-pulse-refresh.yml`) e fica
  bloqueado até o CI voltar a executar (H-05 em [DAY29_HANDOFF.md](DAY29_HANDOFF.md));
- o entregável semanal ("sem provisionamento ou publicação não autorizados") e a
  reconciliação do Dia 28 ("não autoriza deploy, login externo, contratação nem
  provisionamento") continuam valendo como regra: esta reconciliação **amplia o
  escopo do dia, mas não concede autorização**. Cada criação de conta,
  contratação, provisionamento e deploy real exige autorização explícita do
  usuário, por conta e por serviço;
- staging privado não é abertura do produto: os itens obrigatórios antes de abrir
  o produto a outras pessoas (por exemplo, H-08) continuam obrigatórios.

Segredos de produção e staging não são versionados: são variáveis de ambiente
configuradas pelo usuário no painel de cada plataforma.

## Fase 2 — Dias 31 a 40 (planejada em 2026-10-05)

**Decidido pelo usuário em 2026-10-05:** o plano passa de 30 para 40 dias. O nome
deste arquivo é mantido, porque é referência canônica em `AGENTS.md` e em toda a
documentação. Regras desta fase:

- **Pré-requisito:** Dia 30 fechado com evidência. Nenhum dia desta fase começa
  antes disso.
- **Autorização:** cada dia continua exigindo autorização explícita. Este adendo
  registra intenção, não autoriza execução, dependência nova, provider, deploy nem
  publicação.
- **Hierarquia:** os gates abaixo já incorporam a diretriz Particle Atlas, as
  políticas e as ADRs, que prevalecem sobre a descrição resumida de cada dia.

| Dia | Objetivo | Gate objetivo (ajustado às fontes canônicas) |
| --- | --- | --- |
| 31 | Downsampling de séries históricas (janelas 5A e MAX) | Preserva primeiro, último, mínimos, máximos e eventos relevantes, sem interpolação nem forward-fill; gaps continuam gaps (diretriz, §14). `Decimal` exato na API. Algoritmo escolhido em ADR: LTTB puro não garante extremos, M4 ou LTTB com extremos forçados garantem. Contrato via OpenAPI e cliente gerado, sem endpoint inventado. Metas de latência medidas, não presumidas. |
| 32 | Motor gráfico | **Avaliação com medição**, não troca: os gráficos SVG P0 não são reescritos enquanto atenderem desempenho, acessibilidade e fidelidade (diretriz, §18). Lightweight Charts pode ser avaliado, nunca é fonte de verdade; qualquer biblioteca nova exige ADR e verificação em fonte oficial. Valores, rótulos e tabela preservam o valor exato; coordenadas de desenho são só apresentação. `INDEX_100` e TWR nunca compartilham rótulo (ADR-006, ADR-007). |
| 33 | Tokens de cor em Oklch | Mesma semântica: preto, branco e cinza predominam; verde `UP`, vermelho `DOWN`, azul `FLAT`/referência; âmbar só para `STALE` (diretriz, §8). Testes de contraste existentes continuam verdes. O suporte de navegador a Oklch deve ser verificado em fonte oficial antes de adotar. |
| 34 | Revisão do tema claro | O tema claro **já existe** desde o Dia 16 (`[data-theme="light"]` em `apps/web/app/globals.css`). O dia é revisão e derivação dos tokens do Dia 33, com WCAG 2.2 AA nos dois temas. |
| 35 | Neutro final e azul para benchmarks (CDI, IBOV, IPCA) | Compatível com ADR-006, que define azul como `FLAT`/referência. Quando benchmark e `FLAT` aparecem juntos, a distinção vem de padrão de linha, rótulo e tabela, nunca só da cor. |
| 36 | WCAG 2.2 AA e daltonismo | Axe em todas as rotas, mais revisão manual (diretriz, §20). Daltonismo é validado por simulação da paleta existente e pelos sinais não cromáticos obrigatórios. **Paleta alternativa azul/laranja conflita** com a diretriz (laranja só para `STALE`) e com ADR-006 (azul = `FLAT`): só entra com nova ADR. |
| 37 | Global Atlas tabular e heatmap setorial (P0 visual) | **Global Atlas tabular**: tabela acessível, sem recomendação, com disclaimer e metadados visíveis (gate original do Dia 21). **Heatmap básico é P0** (linha "Prioridades do beta" e diretriz, §24) e nunca foi entregue: o Dia 17 o deixou como etapa posterior. Sem suavização; dado real somente com dataset `PUBLIC_APPROVED`; caso contrário, `DEMO` local ou `UNAVAILABLE`. Tabela equivalente obrigatória. |
| 38 | Core Web Vitals no ambiente real | Os budgets já existem desde o Dia 27 (P95 LCP 2.500 ms, INP 200 ms, CLS 0,10, `scripts/day27_performance_gate.mjs`). O dia mede o staging real e audita o bundle, sem relaxar budgets. |
| 39 | Regressão QA completa | Backend, frontend, E2E, testes financeiros, temas, tokens, gráficos e heatmap, nas rodadas oficiais e no CI. |
| 40 | Documentação e fechamento | README, design system e handoff final atualizados; registro de alternativas descartadas (por exemplo Rust, gRPC e FDC3). |

### Lacunas encontradas ao registrar a Fase 2 (2026-10-05)

1. **Global Atlas tabular (P0) nunca foi entregue.** O Dia 21 desta tabela foi
   executado como performance factual de carteiras. A reconciliação do Dia 20 diz
   que o Morning Call viria "antes do Global Atlas", mas nenhum dia posterior o
   recebeu, e não há código dele em `apps/web`. A Fase 2 não o inclui.
2. **Heatmap básico (P0)** aparece só no Dia 37, depois do release candidate do
   Dia 30.
3. **Os itens obrigatórios antes de abrir o produto não estão na Fase 2:** H-08,
   H-09, convite ou allowlist no cadastro (H-11), H-13, H-19, H-21, H-23, Redis
   persistente e plano Vercel adequado a uso não pessoal ([DAY29_HANDOFF.md](DAY29_HANDOFF.md)).
   Sem eles, o Dia 40 não pode declarar o produto pronto para outras pessoas.
4. **Versionamento** (branch `develop` e tags por dia) não foi adotado; decidir no
   Dia 30, junto da tag do release candidate.

**Decidido pelo usuário em 2026-10-05:**

- **Lacunas 1 e 2:** o Global Atlas tabular e o heatmap básico vão juntos para o
  **Dia 37**, depois do release candidate. Por isso o RC do Dia 30 é registrado
  como **RC do staging privado com P0 incompleto**, não como P0 congelado.
- **Lacuna 3:** os itens obrigatórios antes de abrir o produto ficam distribuídos
  assim, somados ao escopo de cada dia:

| Dia | Itens acrescentados | Observação |
| --- | --- | --- |
| 30 | H-08 (ADR da opção B do `note`), H-09 (ordem CSRF x rate limit), decisão sobre convite/allowlist no cadastro (H-11) | H-08 exige ADR e migration com teste; H-09 exige ADR. |
| 35 | H-13 (compliance do Morning Call), H-19 (limite por sessão), H-21 (menos requisições ao balde standard) | H-13 é revisão humana registrada. H-21 prevê endpoint em lote: contrato OpenAPI e cliente gerado. |
| 39 | H-23 (IP real atrás de proxy), Redis persistente (R1 ou R3), plano Vercel adequado ao uso | A medição do IP é feita no staging assim que ele existir. Redis persistente e plano Vercel dependem de contratação pelo usuário. |

**Autorização do usuário em 2026-10-07:** iniciar os Dias 31 a 34 com o gate do Dia 30
ainda aberto. O Dia 30 tem todas as entregas de código feitas e depende só da validação
oficial, que passou a ser o `release-gate.yml` e está bloqueada pela cobrança do GitHub
(H-05). Os Dias 31 a 34 são desenvolvidos na branch `feature/dia-31-34`, sem deploy, e
cada gate registra a evidência medida; a validação oficial em CI fica pendente pelo mesmo
motivo.

**Estado dos Dias 31 a 34 em 2026-10-07** (branch `feature/dia-31-34`, sem deploy):

| Dia | Entrega | Evidência medida | Pendente |
| --- | --- | --- | --- |
| 31 | Downsampling M4 opt-in com divulgação no contrato ([ADR-013](adr/013-history-display-downsampling.md)) | 12 testes de backend (subconjunto exato, extremos, gaps, endpoint); suíte com 380 passed e 0 failed; OpenAPI e cliente regenerados | Redução na comparação multissérie (exige faixas comuns de tempo) |
| 32 | SVG P0 mantido; Lightweight Charts avaliada e não adotada ([ADR-014](adr/014-chart-engine-keep-svg.md)) | Benchmark reproduzível (`apps/web/scripts/chart-benchmark.tsx`); rótulo `INDEX_100` distinto de TWR; teste contra biblioteca sem ADR | Medição de layout e pintura no navegador (Dia 38) |
| 33 | Tokens em OKLCH com fallback hex idêntico ([ADR-015](adr/015-oklch-tokens-and-theme-contrast.md)) | Paridade OKLCH↔hex testada; build preserva `oklch()` | — |
| 34 | Revisão do tema claro: AA completo nos dois temas e borda de controle 3:1 ([ADR-015](adr/015-oklch-tokens-and-theme-contrast.md)) | Matriz de contraste testada (texto ≥ 4,5:1; foco e borda ≥ 3:1) | Tema global e persistente; âmbar do calendário (decisões de design) |

Os quatro gates seguem sem a validação oficial em CI (bloqueio de cobrança, H-05) e sem
revisão visual de Cláudio e do responsável humano.

Ponto de atenção registrado: o H-19 (Dia 35) inclui decidir o IP como segunda
chave, e o IP correto só fica confiável com o H-23 (Dia 39). O Dia 35 deve usar a
medição de IP já feita no staging, ou deixar essa parte explícita para o Dia 39.

**Estado do Dia 35 em 2026-10-07** (branch `feature/dia-31-34`, sem deploy; autorização
do usuário para seguir até o Dia 40):

| Item | Entrega | Evidência medida | Pendente |
| --- | --- | --- | --- |
| H-19 | Limite do balde `standard` por usuário com sessão válida; IP para o resto ([ADR-017](adr/017-per-user-rate-limit.md)) | 5 testes (usuários no mesmo IP, cookie forjado, sessão revogada, anônimo, leitura única da sessão) | IP real por saltos confiáveis (H-23, Dia 39) |
| H-21 | `GET /portfolios/{id}/overview` e watchlists sem recarga total ([ADR-018](adr/018-portfolio-overview-and-aligned-downsampling.md)) | Overview igual aos 8 endpoints separados; isolamento por dono; testes de frontend | Contagem de requisições medida na rodada de frontend |
| Comparação | Downsampling M4 alinhado e opt-in no lote; benchmark tracejado com legenda em texto; ponto principal neutro ([ADR-018](adr/018-portfolio-overview-and-aligned-downsampling.md)) | Mesmas datas em todas as séries, extremos de cada uma preservados; contraste do acento neutro ≥ 3:1 nos dois temas | — |
| H-13 | Avisos canônicos do §11 em todas as áreas financeiras; [pacote de revisão](editorial/MORNING_CALL_COMPLIANCE_REVIEW.md) | Teste compara o texto do código com a política | **Assinatura humana**; divergências do fluxo editorial (H-25) |

Verificações do Dia 35: backend com 391 passed, 10 skipped e 0 failed; frontend com 67
testes unitários, lint, typecheck e build OK; OpenAPI e cliente gerado sincronizados.
Resolve as pendências "redução na comparação multissérie" (Dia 31) e as decisões de
design do Dia 34 ([ADR-016](adr/016-global-persisted-theme.md)). Novos achados: H-24 e
H-25 no [handoff](DAY29_HANDOFF.md). O gate segue sem CI (H-05) e sem deploy no staging.

**Estado do Dia 36 em 2026-10-07** (mesma branch, sem deploy): relatório em
[ACCESSIBILITY_DAY_36.md](design/ACCESSIBILITY_DAY_36.md).

- **Corrigido:** variação do ativo com direção, sinal, seta e palavra (era sempre azul);
  `FRESH` neutro; cotação sem base sem variação inventada; foco em todos os controles;
  link sublinhado no login e no cadastro; `h1` no carregamento das watchlists.
- **Medido:** axe WCAG 2.2 AA nas 9 rotas e nos dois temas, reflow em 320 px, foco por
  teclado e movimento reduzido: 21 de 21 no Playwright local. Simulação de daltonismo da
  paleta existente: a cor sozinha não separa as direções em todas as visões, e os sinais
  não cromáticos cobrem isso. Backend com 392 passed, 10 skipped e 0 failed; frontend com
  73 testes, lint, typecheck e build OK.
- **Pendente:** estados com sessão e com DEMO na varredura (exige CI ou Docker), leitor de
  tela, zoom de 200% e espaçamento de texto (revisão humana). Paleta alternativa não foi
  proposta.

**Estado do Dia 37 em 2026-10-07** (mesma branch, sem deploy;
[ADR-019](adr/019-global-atlas-table-and-basic-heatmap.md)):

- **Entregue:** `/atlas` (Global Atlas em tabela, a partir de `GET /instruments`, que
  deixou de ser stub) e `/heatmap` (heatmap básico com tabela equivalente). O contrato
  declara o que os dados não permitem: agrupamento por tipo de instrumento (sem setor),
  área igual (sem valor de mercado) e cor pela direção.
- **Medido:** backend com 397 passed, 10 skipped e 0 failed; frontend com 77 testes;
  gate WCAG com 11 rotas, 25 de 25 (local, sem sessão e com DEMO desligado). OpenAPI e
  cliente gerado atualizados.
- **Pendente:** dado real exige dataset `PUBLIC_APPROVED`; setor e valor de mercado
  exigem fonte aprovada e nova ADR; revisão visual de Cláudio.

**Estado do Dia 38 em 2026-10-07** ([relatório](engineering/PERFORMANCE_DAY_38.md)):

- **Medido no staging real** (código do Dia 29, 5 execuções por rota, desktop e móvel
  limitado): todas as rotas dentro dos budgets. Maior LCP P95 de 2.252 ms em
  `/portfolios` no perfil móvel; CLS P95 máximo de 0,024; INP de laboratório máximo de
  88 ms. Cold start da API de 52,8 s (H-27).
- **Bundle:** de 172,5 a 185,2 KB gzip de JS por rota, dos quais 171,2 KB são comuns;
  orçamento de regressão de 200 KB.
- **Gate:** passa a verificar as medições reais registradas e o bundle, além das
  fixtures; o caminho de falha foi testado.
- **Pendente:** medir os Dias 30 a 37 depois do deploy (autorização do usuário);
  percentil de campo (H-26); margem de LCP móvel em `/portfolios` e `/calendar`.

**Estado do Dia 39 em 2026-10-07** ([relatório](engineering/REGRESSION_DAY_39.md)):

- **Regressão local:** backend com 407 passed, 10 skipped e 0 failed; frontend com 80
  testes, lint, typecheck e build OK; gate de desempenho OK; E2E de acessibilidade com
  29 de 29.
- **Corrigido:** tabela da comparação pareando valores pela posição (Q-1), escala da
  comparação sem aviso (Q-2), H-22, H-24 e D-5 do H-25.
- **H-23:** mecanismo pronto com testes de forja ([ADR-020](adr/020-trusted-proxy-hops.md));
  ativação pendente de medição no staging.
- **Gate aberto:** faltam as rodadas oficiais em CI (H-05), o E2E com DEMO e as
  contratações (Redis persistente, planos da Vercel e do Render).

### Adendo operacional do Dia 23

O Dia 23 executado corresponde ao CMS administrativo mínimo e ao versionamento
público do Morning Call: papéis `USER`/`EDITOR`/`REVIEWER`/`ADMIN`, workflow
`DRAFT` → `UNDER_REVIEW` → `APPROVED` → `PUBLISHED` → `ARCHIVED`, validação
editorial, eventos de revisão e leitura pública somente de versões publicadas.
O prompt direto prevaleceu sobre a descrição anterior de Neon/Upstash; essa
integração não foi apagada do histórico, apenas permanece trabalho futuro
condicionado a nova autorização. A decisão está detalhada em
[MORNING_CALL_ADMIN_DAY_23.md](editorial/MORNING_CALL_ADMIN_DAY_23.md).

A linha tabular histórica que descrevia Neon/Upstash não é o entregável
canônico do Dia 23; este adendo é a reconciliação normativa e mantém o registro
anterior para rastreabilidade.

### Adendo operacional do Dia 22

O Dia 22 executado corresponde ao validador editorial e ao Morning Call factual,
conforme o prompt aprovado. A linha histórica anterior que previa Stripe em
modo de teste não autoriza integração neste dia; Stripe permanece pendente,
estritamente test-only, para um gate futuro com nova autorização. Nenhuma
cobrança, paywall, IA, provider ou notícia externa foi ativada.

## Gate final do beta

O beta só é aceito quando:

- fluxos P0 funcionam de ponta a ponta e possuem testes essenciais;
- todo dado financeiro mostra fonte, horários, `DataLevel`, `Freshness` e limitação;
- falha de provider degrada para snapshot validado `STALE` ou `UNAVAILABLE`;
- exposição pública de provider obedece `PUBLIC_APPROVED` e default deny;
- conteúdo não contém recomendação, sinal, promessa ou preço-alvo próprio;
- WCAG 2.2 AA e alternativa tabular são verificadas nos fluxos críticos;
- migrações, build, lint, typecheck, testes, smoke e runbooks passam;
- Stripe, se presente, permanece apenas em modo de teste;
- nenhum deploy, contratação ou cobrança real ocorreu sem autorização.

## Fora do escopo preservado

- Stripe em produção, cobrança real, assinatura comercial, paywall e planos pagos.
- WhatsApp, Telegram, e-mail, push, alertas e automações de notificação.
- Chat, texto/insights gerados por IA, recomendações, sinais, suitability ou preço-alvo próprio.
- Apps móveis, corretoras, ordens, gestão de carteira, execução financeira e backtesting.
- WebSockets/tick streaming, microserviços, Kafka, Kubernetes e alta disponibilidade.
- Recuperação de senha, MFA, login social e verificação de e-mail.
- CMS/editor visual, watchlists compartilhadas e integrações não essenciais.
- Globo 3D, Canvas/WebGL, partículas e animações avançadas como requisito de lançamento.
- Provisionamento pago e deploy externo sem autorização posterior.
