# Market Pulse

O Market Pulse é um terminal web autenticado para acompanhamento **informativo e analítico** de mercados financeiros e carteiras próprias. O beta prevê universo aprovado de ativos, dashboard, busca/páginas de ativo, Particle Atlas acessível, Global Atlas tabular, watchlist, carteiras informativas, heatmap, cotações com proveniência e freshness e Morning Call inserido por comando administrativo.

> **Conteúdo informativo. Não constitui recomendação de investimento.**

## Estado verificado — 2026-10-08

As implementações dos Dias 31–39 estão no Git na branch `feature/dia-31-34`; o Dia 40
fechou a entrega documental. Isso **não fecha** os gates dos Dias 31–39 nem valida o
código atual em staging ou produção. A auditoria detalhada e as próximas ações estão no
[handoff final](docs/FINAL_HANDOFF_DAY_40.md), no [handoff de pendências](docs/DAY29_HANDOFF.md)
e nos relatórios ligados na [Fase 2 do roadmap](docs/ROADMAP_30_DAYS.md).

| Categoria | Estado comprovado no repositório | Limite da evidência |
| --- | --- | --- |
| Implementado no código | Dias 31–39; CSP Report-Only do frontend e limites de segurança do CLI de retenção foram acrescentados localmente nesta rodada | Código na branch não significa gate fechado nem implantação |
| Testado localmente | Nesta rodada: API 52 testes direcionados passaram; web 81/81; lint, typecheck, build, OpenAPI e Ruff passaram. A API completa e o E2E não foram executados | Dois testes que exigem Redis/banco descartável foram excluídos; os testes de retenção usaram conexão simulada; não equivale a CI oficial |
| Enviado para GitHub | `origin/feature/dia-31-34` e `origin/feature/dia-29-staging` continuam em `17471845c9a22719d2a84b1b7df4cf6ed7d288f7`; `e967b36` e esta integração são locais e não foram enviados | Referência Git não comprova deploy |
| Deploy automático configurado | `render.yaml` configura deploy do serviço da API por commit na branch `feature/dia-29-staging`; documentos do staging registram a Vercel ligada a essa mesma branch | O projeto e os controles atuais dos painéis Vercel/Render não foram revalidados nesta auditoria |
| Deploy confirmado | O runbook registra o staging com código do Dia 29, commit `60df9ca`, URLs e smoke | Não há evidência de deploy do HEAD local nem consulta atual ao painel |
| Staging validado | Smoke e sessão foram medidos para o código do Dia 29 (`60df9ca`) | Dias 30–40 ainda não foram promovidos/validados nesse ambiente |
| Produção validada | Nenhuma validação de produção com commit, URL e smoke foi encontrada | Estado do deployment atual da Vercel não foi consultado; não presumir que esteja inalterado |
| Bloqueadores externos | Billing do GitHub, serviços/planos e variáveis em painéis, aprovação de deploy e licença de dados | H-05 é reportado nos documentos, mas seu estado atual não foi conferido no painel e não é o único bloqueador |
| Pendências humanas | Assinatura H-13, decisões editoriais, revisão visual e de acessibilidade, revisão jurídica e aprovação manual | Não substituídas por documentação ou testes automáticos |
| Pendências técnicas | CI oficial, convite, validação de CSP no navegador/staging, medição dos proxies, Cron de retenção e reconciliação do roadmap | Detalhadas abaixo e nos handoffs |

**Percentuais do trecho final do roadmap (Dias 31–50, 20 marcos com o mesmo peso):**

- Implementação de código: **45%** (9/20 marcos com a entrega principal de código verificada; outros artefatos parciais não contam como marco entregue).
- Testes locais: **45%** (9/20 marcos com evidência local registrada; não equivale a CI oficial).
- Documentação no README: **100%** (resumo e estado descritos para os 20 marcos; não significa que documentos jurídicos existam ou estejam aprovados).
- Staging: **0%** dos marcos 31–50 implantados e validados; o smoke anterior é do código do Dia 29.
- Produção: **0%** dos marcos 31–50 validados em produção.
- Projeto total: **5%** dos gates dos marcos 31–50 fechados (1/20: Dia 40). Isso mede gates deste trecho, não um percentual ponderado de todo o produto.

O roadmap canônico em `docs/ROADMAP_30_DAYS.md` contém reconciliação até o Dia 40. A
seção abaixo registra, neste README, o plano final pedido para os Dias 41–50; a fonte
canônica ainda precisa de reconciliação documental em uma tarefa autorizada. Registrar
um marco planejado não autoriza iniciá-lo nem declara seu gate aprovado.

### Dias 31–40 — auditoria do estado real

| Dia | Estado | Evidência e pendência principal |
| --- | --- | --- |
| 31 | PARCIAL | M4 opt-in, contrato e testes existem; redução multissérie foi acrescentada no Dia 35; CI oficial pendente. |
| 32 | PARCIAL | SVG P0 mantido, benchmark e distinção `INDEX_100`/TWR testados; layout e pintura no navegador ainda não medidos. |
| 33 | PARCIAL | Tokens OKLCH, fallback hex e testes existem; validação oficial e revisão visual humana pendentes. |
| 34 | PARCIAL | Contraste AA e borda de controle testados; gates oficiais e revisão visual permanecem pendentes. |
| 35 | PARCIAL | Rate limit por usuário, overview, downsampling alinhado e avisos estão no código e têm testes; assinatura H-13 e validações de staging/CI pendentes. |
| 36 | PARCIAL | Verificações automáticas registradas; leitor de tela, zoom de 200%, estado autenticado/DEMO e revisão humana pendentes. |
| 37 | PARCIAL | Global Atlas tabular e heatmap básico têm contrato, implementação e testes; revisão visual e licença PUBLIC_APPROVED para dados reais pendentes. |
| 38 | COMPLETO | Medição de staging registrada e bundle do código atual medido; a medição de staging é do commit `60df9ca` e precisa ser repetida após uma promoção autorizada. |
| 39 | PARCIAL | Regressão local e correções testadas; CI oficial, E2E com DEMO e ativação segura dos saltos de proxy ainda pendentes. |
| 40 | COMPLETO | Design system, alternativas descartadas e handoff documental publicados; isso não fecha os gates técnicos anteriores. |

## Roadmap final — Dias 41 a 50

O Dia 50 é o último marco deste plano final. “Último dia do roadmap” não significa que o
trabalho esteja concluído. As etapas abaixo estão planejadas ou parciais conforme a
evidência no repositório; nenhuma autoriza deploy em produção.

### Dia 41 — Desbloqueio externo e isolamento de ambientes

**Status: PENDENTE.** `render.yaml` descreve somente recursos de staging: API, banco e Key
Value separados entre si, branch `feature/dia-29-staging` e deploy por commit. Não há
recursos de produção, Redis de produção, configuração de separação de secrets por ambiente,
GitHub Environments ou evidência de aprovação manual de produção no repositório. Não existe
`vercel.json`; a configuração da Vercel, GitHub, Neon, Upstash e Cloudflare não foi
consultada. Os painéis precisam confirmar o isolamento antes de qualquer deploy. Os nomes
de variáveis que a configuração do serviço da API precisa definir por ambiente incluem
`MARKET_PULSE_ENVIRONMENT`, `MARKET_PULSE_DATABASE_URL`, `MARKET_PULSE_REDIS_URL`,
`MARKET_PULSE_INTERNAL_REFRESH_SECRET`, `MARKET_PULSE_CORS_ORIGINS`,
`MARKET_PULSE_AUTH_COOKIE_SECURE`, `MARKET_PULSE_AUTH_COOKIE_SAMESITE`,
`MARKET_PULSE_REGISTRATION_ENABLED` e `MARKET_PULSE_TRUSTED_PROXY_HOPS`; nenhum valor foi
consultado ou incluído aqui. O runbook do frontend lista `MARKET_PULSE_API_PROXY_ORIGIN` e
`NEXT_PUBLIC_API_BASE_URL`; confirmar aplicação e escopo no painel antes de definir valores.
H-05 é reportado como bloqueio histórico de cobrança do GitHub, mas o estado atual precisa
ser confirmado no painel.

### Dia 42 — Infraestrutura de staging

**Status: PENDENTE.** O Blueprint do Render configura auto deploy por commit na branch
`feature/dia-29-staging`, banco e Key Value de staging e health check `/health/live`.
Não há Cron de retenção nem evidência versionada de GitHub Environments, secrets separados
ou gate manual de produção. Os runbooks identificam a branch também como origem da produção
Vercel; não a trate como staging isolado. Nenhum painel foi revalidado e não há prova de
deploy do código local. O smoke registrado é do commit `60df9ca`.

### Dias 43–44 — Segurança operacional

**Status: PARCIAL.** A API envia CSP aplicado (`default-src 'self'`). O frontend agora
envia `Content-Security-Policy-Report-Only` com uma política observacional restrita; não há
endpoint coletor, `report-uri` ou `report-to`, e a política não bloqueia conteúdo. Ela ainda
precisa ser observada em navegador e staging. A cadeia de proxy não foi medida nesta rodada;
`MARKET_PULSE_TRUSTED_PROXY_HOPS` segue `0`, e os cabeçalhos encaminhados continuam
ignorados nesse modo. Não aumentar esse valor antes de medir a cadeia e fechar o acesso
direto à API. CSRF/Origin, rate limit por usuário e IP e proteção contra falsificação do
prefixo de `X-Forwarded-For` estão implementados e cobertos por testes locais.

### Dias 45–47 — Jurídico e compliance

**Status: BLOQUEADO EXTERNAMENTE/HUMANAMENTE.** Não foram encontrados Privacy Policy,
Terms of Use, identificação aprovada do controlador, canal de atendimento, registro de
aceite ou inventário jurídico completo. Exportação Decimal, anonimização, RBAC editorial,
validador lexical, histórico append-only e disclaimers estão no código; isso não constitui
aprovação jurídica. Permanecem pendentes texto final, base legal, prazo de retenção,
avaliação jurídica e assinatura H-13.

As rotas atuais restringem aprovação/publicação a `REVIEWER` ou `ADMIN`, mas `ADMIN` também
pode criar posts; não há regra de duas pessoas que impeça o mesmo administrador de publicar
o próprio conteúdo. A segregação de funções e o fluxo editorial precisam de decisão/ADR.

Fluxo alvo solicitado para o plano, ainda não implementado:
`DRAFT → AUTOMATED_CHECK → COMPLIANCE_REVIEW → APPROVED → PUBLISHED`.
A política canônica hoje define `DRAFT → VALIDATION_FAILED ou VALIDATED → IN_REVIEW → PUBLISHED → SUPERSEDED`; o código usa `DRAFT → UNDER_REVIEW → APPROVED → PUBLISHED → ARCHIVED`. A divergência D-1/D-3 exige decisão humana e ADR antes de alteração do fluxo. Não inventar texto jurídico definitivo.

### Dias 48–49 — Governança de dados e retenção

**Status: PARCIAL.** A rotina mantém dry-run como padrão, proteção de `audit_logs`,
`portfolio_events` e ledger, ordem por dependência e transação. Nesta rodada, `--execute`
passou a exigir `--max-rows` e `--batch-size`; todos os alvos são contados antes de qualquer
exclusão, volume acima do limite aborta e cada tabela é verificada antes do commit. A CLI
registra contagens `RETENTION_BEFORE` e `RETENTION_AFTER`; testes locais simulados cobrem
limite, lotes e rollback. A integração com PostgreSQL descartável não foi executada. Não há
Render Cron. O workflow a cada 15 minutos é de refresh de mercado em `DRY_RUN`, não de
retenção. O expurgo continua irreversível após commit; Cron futuro precisa de dry-run,
limites revisados e aprovação humana.

### Dia 50 — Fechamento e promoção

**Status: PARCIAL — checklist documentado, gates não executados.** O roteiro de fechamento é:

1. CI aprovado e migrations revisadas;
2. confirmar um destino de staging isolado e autorizado; registrar SHA implantado;
3. verificar `/health/live` e `/health/ready`;
4. smoke de login, portfolios, compare, Atlas, heatmap e watchlists;
5. E2E crítico, acessibilidade, teclado e zoom de 200%;
6. verificar rate limit, `audit_logs`, migrations e revisão de segurança;
7. concluir revisão jurídica, compliance e aprovação humana;
8. obter aprovação manual de produção antes da promoção.

Dia 50 é o último dia do roadmap, mas não prova que os gates anteriores passaram. Produção
exige aprovação humana e não deve ser promovida automaticamente. O estado descrito para
a branch `feature/dia-29-staging` (deploy por commit na Vercel) conflita com esse controle
e precisa ser verificado/resolvido antes de qualquer push ou promoção.

### Status de promoção e ressalva de Git

> O push para `feature/dia-29-staging` foi realizado anteriormente, mas push não equivale a deploy concluído. O deploy só deve ser considerado confirmado com evidência do provedor, commit implantado, URL e smoke test.

O HEAD local (`e967b36` mais esta integração) está à frente dos refs remotos, que continuam
em `17471845c9a22719d2a84b1b7df4cf6ed7d288f7`. Isso não confirma qual commit está
implantado. Como o runbook identifica `feature/dia-29-staging` como branch de produção da
Vercel, nenhum novo push deve ser feito para ela até que a topologia e a aprovação manual
sejam confirmadas.

#### Próxima validação de staging (não executada)

1. Confirmar nos painéis GitHub, Vercel e Render que a branch/serviço selecionado é isolado
   de produção e que produção exige aprovação manual.
2. Confirmar os nomes de variáveis aplicáveis e configurar valores separados diretamente
   nos respectivos ambientes, nunca no Git ou neste documento.
3. Só após autorização específica, implantar o SHA aprovado no staging confirmado e
   registrar o SHA efetivamente servido.
4. Executar `/health/live`, `/health/ready`, smoke de login, portfolios, compare, Atlas,
   heatmap e watchlists, além do E2E e das revisões de acessibilidade/segurança.
5. Registrar evidências antes de qualquer pedido de promoção; produção permanece pendente
   de aprovação humana explícita.

### Plano local futuro para agendar retenção

- Horário e fuso: definir no painel somente depois de um gate e da confirmação do ambiente.
- Comando inicial: `python -m app.cli.retention --dry-run`; revisar as contagens antes/depois.
- `X-Cron-Secret`: não se aplica ao CLI que conecta direto ao banco; essa credencial é do
  endpoint atual de refresh. Não criar segredo ou endpoint de retenção sem decisão própria.
- Apply futuro: escolher e revisar `--max-rows` e `--batch-size` a partir do dry-run; exige
  aprovação humana para cada configuração. `--execute` sem os dois limites aborta.
- Monitoramento: preservar stdout/stderr do job, observar código de saída, abortos e
  contagens `RETENTION_BEFORE`/`RETENTION_AFTER`; alertas e retenção desses logs dependem
  de configuração externa ainda não verificada.

### Pode começar agora / depende de terceiros

- **Pode começar localmente:** preparar inventário jurídico para revisão humana, observar
  CSP Report-Only no navegador local e revisar o dry-run de retenção sem apagar dados.
- **Bloqueado externamente ou por aprovação humana:** desbloqueio/validação do GitHub
  Actions; configuração de ambientes, secrets e recursos em
  Render/Vercel/Neon/Upstash/Cloudflare; medição de proxy no staging; planos de
  Redis/Vercel/Render; aprovação de licenças de dados;
  assinatura H-13, ADRs editoriais e revisão jurídica/acessibilidade.
- **Não fazer sem nova autorização específica:** configurar billing ou secrets reais,
  alterar Render/Vercel, criar Cron de retenção, publicar texto jurídico, ativar CSP
  enforced, enviar novo push para a branch ligada à produção ou fazer deploy de produção.

O estado histórico dos Dias 29–40 permanece no [handoff final](docs/FINAL_HANDOFF_DAY_40.md),
no [runbook do staging](docs/operations/STAGING_RUNBOOK_DAY_29.md), no
[runbook de promoção](docs/operations/STAGING_PROMOTION_DAYS_30_40.md) e no
[checklist de compliance](docs/COMPLIANCE_CHECKLIST.md).

## Linha do tempo até o Dia 50

| Período | Entrega | Situação |
| --- | --- | --- |
| Dias 1 a 23 | Fundação, API versionada, providers atrás de licença, dados públicos `DEMO`, shell e gráficos Particle Atlas, autenticação, watchlists, carteiras e performance factual, Morning Call | Entregues; critérios dos gates semanais em `docs/engineering/WEEK_*_GATE.md` |
| Dias 24 a 28 | DEMO local isolado, painel interno, comparação multiativo, calendário, proventos, telemetria e hardening | Fechados por decisão do usuário |
| Dia 29 | Staging privado na Vercel e no Render | No ar; gate aberto (rodadas oficiais) |
| Dia 30 | RC do staging privado: ADR-009, ADR-010 e decisão de convite | Gate aberto; sem deploy |
| Dias 31 a 39 | Downsampling, tokens OKLCH, tema, limite por usuário, overview da carteira, avisos legais, WCAG 2.2 AA, Global Atlas e heatmap, Web Vitals, regressão | Implementações no Git; gates conforme a tabela de auditoria, staging não validado para o código atual |
| Dia 40 | Documentação e handoff | Fechado |
| Dias 41–42 | Isolamento e staging | Dependem de configuração e validação externa |
| Dias 43–44 | Segurança operacional | CSP Report-Only local; observação e proxy em staging pendentes |
| Dias 45–47 | Privacidade e Morning Call | Controles de código existentes; jurídico, assinatura humana e ADR pendentes |
| Dias 48–49 | Retenção e auditoria | CLI limitado e testado com fakes; DB descartável e Cron não validados/configurados |
| Dia 50 | Gate final | Checklist atualizado; CI, staging, revisões e aprovação humana pendentes |

O que cada dia provou, e com que evidência, está na seção "Fase 2" do
[roadmap](docs/ROADMAP_30_DAYS.md), nos relatórios dos Dias 35–39 e na tabela acima.

## Demonstração local — Dia 24

Consulte [DEMO_SEED_DAY_24.md](docs/demo/DEMO_SEED_DAY_24.md) para os comandos,
barreiras, dados sintéticos e gates executados. O único banco autorizado para
reset ou seed é `market_pulse_demo`, local e isolado. Nunca execute limpeza,
reset ou a suíte integrada contra o banco principal.

O workflow isolado [Day 24 DEMO Integration Gate](.github/workflows/demo-integration.yml)
executa migrations e os tres testes criticos de seed/reset em Postgres e Redis
efemeros. Ele roda em PRs que tocam o fluxo DEMO, nightly e por
`workflow_dispatch`; nao faz parte do job principal de qualidade.

## Escopo P0 do beta

- Dashboard responsivo em tema escuro.
- Componentes selecionados do Ibovespa; dez ações americanas; Ibovespa, S&P 500 e Nasdaq; USD/BRL; ouro, Brent e WTI.
- Ações selecionadas, ETFs e FIIs somente quando houver fonte aprovada/licenciada; fundos tradicionais são P1 condicionado.
- Particle Atlas P0: design system, componentes/estados, metadados visíveis e acessibilidade WCAG 2.2 AA.
- Global Atlas P0 em tabela acessível; globo 3D é P1 condicional e não bloqueia o beta.
- API FastAPI versionada sob `/api/v1` e contrato OpenAPI.
- PostgreSQL como fonte persistente e Redis como cache/lock.
- Providers substituíveis, license gate e fallback para último snapshot validado.
- `source`, timestamps, `DataLevel`, `Freshness` e limitações em dados financeiros.
- Cadastro por e-mail/senha com sessão opaca em cookie `HttpOnly`.
- Watchlist por usuário e heatmap básico. Sem dataset aprovado com setor e valor de mercado, o heatmap agrupa por tipo de instrumento, com área igual ([ADR-019](docs/adr/019-global-atlas-table-and-basic-heatmap.md)).
- Múltiplas carteiras próprias, ledger manual e cálculos factuais de posição, custo, patrimônio, P&L, rentabilidade, proventos e performance.
- Morning Call sem IA, inserido por comando interno e publicado após revisão humana.
- Testes essenciais, documentação, observabilidade e artefatos de deploy, sem publicação automática.

## Limites do produto

O produto não fornece gestão de carteira, compra/venda/manutenção, sinal, preço-alvo próprio, timing, alocação, suitability, promessa de resultado, execução em corretora ou orientação personalizada. Carteiras são registros informativos do usuário. Dados `DELAYED`, `EOD`, `DEMO` ou `STALE` nunca podem ser apresentados como tempo real/atual.

Stripe pode ser considerado no beta **somente em modo de teste**, isolado e opcional, no Dia 22 e mediante novo gate. Cobrança real, produção, assinatura comercial, paywall e planos pagos permanecem fora do escopo. Também não entram notificações, WhatsApp, Telegram, e-mail, push, IA, apps móveis, streaming tick a tick ou arquitetura de alta escala.

## Arquitetura resumida

- `apps/web`: Next.js App Router, React e TypeScript strict; gráficos em SVG
  ([ADR-014](docs/adr/014-chart-engine-keep-svg.md)) e tokens em
  [design system](docs/design/DESIGN_SYSTEM.md).
- `apps/api`: FastAPI e Alembic, monólito modular sob `/api/v1`.
- Carteiras: ledger factual, append-only e isolado por usuário, com cálculos no domínio/backend.
- PostgreSQL: fonte persistente. Redis: sessões, rate limit e cache não autoritativo.
- Staging: web na Vercel com proxy same-origin para a API
  ([ADR-008](docs/adr/008-same-origin-api-proxy.md)); API, Postgres e Key Value no Render
  pelo Blueprint `render.yaml`.
- Refresh: processo curto e idempotente para um endpoint interno protegido; o agendamento
  pelo GitHub Actions está bloqueado (H-05).

Leia a [arquitetura canônica](docs/ARCHITECTURE.md) e as [ADRs](docs/adr/).
A [baseline enterprise de engenharia](docs/engineering/ENTERPRISE_ENGINEERING_BASELINE.md) é a constituição técnica para qualquer alteração futura.
O gate operacional da Semana 1 está documentado em [WEEK_1_GATE.md](docs/engineering/WEEK_1_GATE.md).

## Documentação canônica

| Documento | Finalidade |
| --- | --- |
| [Especificação](docs/PROJECT_SPEC.md) | Escopo, prioridades e decisões do produto |
| [Roadmap de 30 dias](docs/ROADMAP_30_DAYS.md) | Entregáveis, dependências e gates diários |
| [Arquitetura](docs/ARCHITECTURE.md) | Componentes, fronteiras, segurança e operação |
| [Política financeira](docs/policies/FINANCIAL_CONTENT_POLICY.md) | Limites editoriais e publicação |
| [Plano da fronteira financeira](docs/superpowers/plans/financial-content-boundary.md) | Tradução técnica futura da política |
| [Matriz de licenças](docs/DATA_PROVIDER_LICENSE_MATRIX.md) | Evidências e aprovação por combinação de uso |
| [Diretriz Particle Atlas](docs/design/PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md) | Contrato visual, de gráficos, carteiras e integração frontend |
| [Governança de dados](docs/DATA_GOVERNANCE.md) | Proveniência, timestamps, licença e qualidade |
| [Versionamento da API](docs/API_VERSIONING.md) | Política de `/api/v1` e compatibilidade |
| [SLO inicial](docs/SLO.md) | Objetivos mensuráveis, ainda não SLA |
| [Instruções operacionais](AGENTS.md) | Hierarquia, segurança, execução e Definition of Done |
| [ADRs](docs/adr/README.md) | Índice das decisões aceitas (001 a 020), com estado de implementação e de deploy |
| [Design system](docs/design/DESIGN_SYSTEM.md) | Tokens, semântica e componentes implementados |
| [Handoff final](docs/FINAL_HANDOFF_DAY_40.md) | Estado da Fase 2 e próximas ações |
| [Checklist de compliance](docs/COMPLIANCE_CHECKLIST.md) | Controles, evidências e lacunas para auditoria |
| [Promoção dos Dias 30 a 40](docs/operations/STAGING_PROMOTION_DAYS_30_40.md) | Deploy no staging, smoke e rollback, quando autorizado |

`roadmap-30-days.md`, `architecture-overview.md`, `financial-content-policy.md`, `financial-content-boundary-plan.md` e `docs/CODEOWNERS` são registros históricos com links para suas fontes atuais.

## Licenciamento de dados

Licenciamento é `default deny` por provider, plano, endpoint, dataset, finalidade e modalidade. Nenhum candidato externo está aprovado no Dia 1. Apenas uma combinação `PUBLIC_APPROVED`, sustentada por evidência oficial atual, poderá alimentar exposição pública. Gratuidade, `DEMO`, autenticação administrativa ou feature flag não concedem direitos.

## Configuração futura

`.env.example` contém somente nomes e valores vazios/fictícios. Segredos reais devem ser injetados por ambiente autorizado; `.env`, `credentials.json`, chaves e tokens não são versionados.

As versões-alvo são Node.js 24.20.0, pnpm 11.25.0, Python 3.14.7 e uv 0.12.7. O ambiente usado no scaffold registrou Node.js 22.19.0 e Python 3.11.9, gerando aviso de engine no pnpm; alinhar as versões-alvo antes de promover o ambiente.

## Comandos operacionais do scaffold

```powershell
# instalar dependências do workspace web e sincronizar a API
pnpm install
python -m uv sync --project apps/api --group dev

# serviços de apoio locais (Docker Desktop em execução)
docker compose up -d postgres redis
docker compose down

# desenvolvimento
pnpm --filter @market-pulse/web dev
python -m uv run --directory apps/api uvicorn app.main:app --reload

# qualidade web
pnpm --filter @market-pulse/web lint
pnpm --filter @market-pulse/web typecheck
pnpm --filter @market-pulse/web test
pnpm --filter @market-pulse/web build

# qualidade API
python -m uv run --directory apps/api ruff check app tests
python -m uv run --directory apps/api python -m pytest
python -m uv run --directory apps/api alembic upgrade head

# contrato OpenAPI e cliente TypeScript
Invoke-WebRequest http://127.0.0.1:8000/openapi.json -OutFile docs/api/openapi.json
pnpm --filter @market-pulse/web generate:api

# diagnóstico local
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

Em Linux/macOS, use os mesmos comandos em shell POSIX (`docker compose ...`, `curl http://127.0.0.1:8000/health/live` e `curl -i http://127.0.0.1:8000/health/ready`). Para simular indisponibilidade, execute `docker compose stop postgres` ou `docker compose stop redis`; restaure com `docker compose start postgres redis`. O endpoint `/health/live` independe dos serviços; `/health/ready` retorna `503` quando qualquer dependência falha.

O endpoint `/health` mantém compatibilidade e retorna diagnóstico simples. Os endpoints novos diferenciam processo vivo de dependências prontas, sem expor credenciais ou strings de conexão.

A API pública usa `/api/v1`, Problem Details (`application/problem+json`) e
`Idempotency-Key` obrigatório para eventos de carteira. O snapshot está em
`docs/api/openapi.json`; o cliente gerado fica em `apps/web/src/generated/api.ts`.
Valores monetários são serializados como strings decimais para preservar exatidão.

## Verificações

| Verificação | Comando |
| --- | --- |
| Backend | `python -m uv run --directory apps/api python -m pytest -q` |
| Frontend | `pnpm --filter @market-pulse/web lint`, `typecheck`, `test` e `build` |
| Desempenho e bundle | `node scripts/day27_performance_gate.mjs` (depois do build) |
| Bundle por rota | `node apps/web/scripts/bundle-audit.mjs` (dentro de `apps/web`) |
| Acessibilidade | `pnpm --dir apps/web exec playwright test e2e/day36-wcag.spec.ts` (web e API locais no ar) |
| Web Vitals num ambiente real | `BASE_URL=https://... node apps/web/performance/measure-vitals.mjs` |

Verificação indisponível nunca deve ser descrita como aprovada.

## Contribuição e segurança

Leia [AGENTS.md](AGENTS.md), confirme o dia no [roadmap](docs/ROADMAP_30_DAYS.md), use Conventional Commits e preencha o [template de pull request](.github/PULL_REQUEST_TEMPLATE.md). Não faça push, deploy, login externo ou contratação sem autorização explícita.

Não publique credenciais, dados pessoais ou vulnerabilidades exploráveis. Consulte [SECURITY.md](SECURITY.md).

## Licença do repositório

O repositório não adota licença open source neste momento; consulte [LICENSE](LICENSE). Licença de código e licença de dados são assuntos separados.

## Próximo passo

Seguir a ordem da seção 3 do [handoff final](docs/FINAL_HANDOFF_DAY_40.md): desbloquear o
CI (H-05), autorizar o deploy dos Dias 30 a 40 no staging, assinar a revisão de
compliance do Morning Call e decidir os planos. As alternativas descartadas estão em
[DISCARDED_ALTERNATIVES.md](docs/engineering/DISCARDED_ALTERNATIVES.md).
