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
| 27 | Logs estruturados, health, runbooks e OpenAPI | Operação | Correlação funciona; logs não contêm segredo/cookie/body bruto |
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
