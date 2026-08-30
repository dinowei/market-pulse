# Market Pulse — Roadmap definitivo de 30 dias

- **Status:** Aprovado
- **Premissa:** 30 dias corridos, uma pessoa com uso intensivo do Codex
- **Regra:** Cada dia exige autorização e dependências satisfeitas; gates exigem evidência reproduzível.

## Semana 1 — Fundação e contratos

| Dia | Objetivo | Dependências | Entregáveis | Riscos | Critério de aceite | Fora de escopo |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Fundação/governança | Repo novo | Spec, roadmap, arquitetura, políticas, ADRs, segurança, CI documental, commit/export | Contradição/licença | Auditoria documental/segredos verde | Código e integrações |
| 2 | Scaffold web/API | Dia 1 aprovado | Next.js/FastAPI mínimos e lockfiles | Versões | Apps iniciam e checks básicos passam | Domínio/banco |
| 3 | Ambiente local | Dia 2 | Dockerfiles, Compose, PostgreSQL/Redis | Volumes | Serviços saudáveis sem segredo | Deploy |
| 4 | Persistência | Dia 3 | SQLAlchemy, Alembic e primeira migração | Modelo prematuro | Upgrade/downgrade em banco vazio | Provider real |
| 5 | Contrato HTTP | Dia 4 | `/api/v1`, health, Problem Details e OpenAPI | Instabilidade | Contract tests/schema passam | Features finais |
| 6 | Fronteira provider | ADR-004/API | Protocol, fake adapter, license gate e fixtures | Bloqueio incorreto | Não autorizado não chega ao público | Provider real |
| 7 | Gate semanal | Dias 2–6 | CI executável, testes-base e docs | Checks divergentes | Gate reproduzível | UI final |

**Gate Semana 1:** apps mínimos, banco/cache, migração, fake provider, contrato, license gate e quality checks possuem evidência.

## Semana 2 — Dados e resiliência

| Dia | Objetivo | Dependências | Entregáveis | Riscos | Critério de aceite | Fora de escopo |
| --- | --- | --- | --- | --- | --- | --- |
| 8 | Adapter inicial | Licença confirmada | Primeiro adapter e contratos | Redistribuição | Matriz contém fonte/permissão | Segundo provider |
| 9 | Normalização | Adapter | Ativo, símbolo, moeda e timestamps | Semântica | Fixtures determinísticas | Cache |
| 10 | Cache/fallback | Snapshots válidos | Cache-aside e fallback por ativo | Stale silencioso | Clock tests fresh/stale | Scheduler |
| 11 | Refresh manual | Idempotência | Comando/endpoint interno e ingestion runs | Replay | Repetição não duplica | Cron recorrente |
| 12 | API de mercado | Normalização | Assets, quotes e overview | Falha parcial | Mistura fresh/stale correta | Dashboard final |
| 13 | Heatmap backend | Universo/taxonomia | Agregação setor/market cap | Licença de peso | Peso/variação verificáveis | Visual final |
| 14 | Gate de resiliência | Dias 8–13 | Timeout, rate limit, payload inválido e recovery | Flakiness | Suite sem rede descontrolada | Novo provider |

**Gate Semana 2:** provider autorizado, proveniência, fallback, refresh idempotente, métricas e bloqueio de exposição têm evidência.

## Semana 3 — Produto e experiência

| Dia | Objetivo | Dependências | Entregáveis | Riscos | Critério de aceite | Fora de escopo |
| --- | --- | --- | --- | --- | --- | --- |
| 15 | Design system | Contrato | Tema, tokens, shell e estados | A11y | 360/1440 px sem overflow | Gráficos finais |
| 16 | Dashboard | API mercado | Cards, índices, FX, commodities | Densidade | Fonte/tempo/stale visíveis | Streaming |
| 17 | Heatmap | Agregação | Treemap e tabela acessível | Performance | Área/cor/teclado testados | Histórico |
| 18 | Identidade | Persistência | Cadastro/login/logout/me | Abuso/CSRF | Cookie/Origin testados | Recovery/MFA/social |
| 19 | Watchlist | Identidade | Lista persistida | Autorização horizontal | Isolamento por usuário | Compartilhar |
| 20 | Morning Call | Política | Comando admin, versões e display | Conteúdo impróprio | Falha bloqueia draft; humano publica | IA/editor |
| 21 | Conta/gate UX | Dias 15–20 | Conta, entitlement beta e integração | Scope creep | Fluxos/disclaimer passam | Billing/planos |

**Gate Semana 3:** dashboard, heatmap, sessão, watchlist e Morning Call funcionam de forma acessível; entitlement é beta único.

## Semana 4 — Hardening e release candidate

| Dia | Objetivo | Dependências | Entregáveis | Riscos | Critério de aceite | Fora de escopo |
| --- | --- | --- | --- | --- | --- | --- |
| 22 | Monetização adiada | Escopo | Registro sem billing | Scope creep | Nenhuma dependência Stripe | Billing |
| 23 | Integração infra | Stack | PostgreSQL/Redis/migração/clock tests | Ambiente | Banco vazio/fallback passam | HA |
| 24 | Frontend/a11y | UX | Component/unit/a11y tests | Falso positivo | Estados críticos cobertos | Pixel perfection |
| 25 | E2E | Integração | Conta, dashboard, watchlist, stale e Morning Call | Flakiness | E2E determinístico | Provider ao vivo CI |
| 26 | Segurança | E2E verde | CORS, cookies, headers, rate limit | Regressão | Testes de abuso passam | Auditoria externa |
| 27 | Observabilidade/docs | Operação | Logs, health, runbooks e OpenAPI | Segredo em log | Smoke/inspeção passam | Plataforma paga |
| 28 | Artefatos produção | Checks | Imagens, non-root, shutdown e health | Diferença prod | Smoke local equivalente | Publicação |
| 29 | Ensaio deploy | Artefatos | Configuração e runbook | Lock-in/custo | Dry run local sem login | Deploy real |
| 30 | Release candidate | Gates | Regressão, limitações e checklist | Bloqueador tardio | Critérios MVP evidenciados | Expansão |

**Gate Semana 4:** suite, migrações, segurança, observabilidade, smoke local e release checklist verdes; nenhum deploy externo.

## Fora do escopo preservado

- Stripe, billing, assinatura, paywall e planos pagos.
- WhatsApp, Telegram, e-mail, push e alertas.
- Chat, IA generativa, insights ou recomendações.
- Apps móveis, corretoras, ordens, carteira, P&L e backtesting.
- Streaming, microserviços, Kafka, Kubernetes e alta disponibilidade.
- Recovery, MFA, login social e verificação de e-mail.
- CMS visual, watchlists compartilhadas e integrações não essenciais.
- Provisionamento pago e deploy externo sem autorização.
