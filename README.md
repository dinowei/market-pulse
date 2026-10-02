# Market Pulse

O Market Pulse é um terminal web autenticado para acompanhamento **informativo e analítico** de mercados financeiros e carteiras próprias. O beta de 30 dias terá universo aprovado de ativos, dashboard, busca/páginas de ativo, Particle Atlas acessível, Global Atlas tabular, watchlist, carteiras informativas, heatmap setorial, cotações com proveniência e freshness e Morning Call inserido por comando administrativo.

> **Conteúdo informativo. Não constitui recomendação de investimento.**

## Status atual

Os **Dias 24 a 27** estão fechados: autenticação, watchlists, carteiras,
Morning Call, demonstração local persistida e isolada, painel operacional
interno, comparação multiativo, calendário econômico, proventos, marcadores e
telemetria Web Vitals. Nenhum provider real, Stripe ou deploy foi ativado.

O **Dia 28** (hardening enterprise) está **FECHADO em 2026-10-01**, por decisão do
usuário. Entregas: remoção de endpoint sem autenticação, CSRF unificado para todo
método mutante, cabeçalhos de segurança, validação estrita de configuração de
produção, exclusão de conta por anonimização com revogação de todas as sessões e
auditoria atômica, export de dados com valores decimais, backup/restore com
verificação de integridade (`REDIS_SNAPSHOT=OK|NAO_SUPORTADO|INDISPONIVEL`) e
expurgo de registros operacionais.

Evidência de fechamento, por origem (2026-10-01):

**Medida por Claude Code** (Neon `dev` + Upstash):

- Suíte de backend: **341 passed, 1 failed, 10 skipped** em 111 s. A falha é
  `test_demo_browser_day24`, que depende de Redis local não declarado (503 no lugar
  de 403); o login forjado é recusado de qualquer forma. Os 10 skips são testes
  opt-in que exigem banco local descartável. Números observados, não meta.
- Testes unitários do frontend: 33 passed; `tsc` e `eslint` limpos.
- Expurgo (`python -m app.cli.retention`, dry-run por padrão) executado de verdade
  em Postgres descartável: 14 de 14 verificações. Restore com paridade de tabelas.

**Executada e informada pelo responsável** (logs fora do repositório, não conferidos
por Claude Code):

- **Rodada 1** (`run_local.ps1`, 21:11): E1–E13 OK, teste negativo com 10 skipped,
  11 testes opt-in passed (inclui a anonimização ponta a ponta em banco real),
  retenção em dry-run OK.
- **Rodada 2** (`run_frontend.ps1`, 22:02): 33 testes unitários passed, build OK, E2E
  6 passed (a11y 4, principal 1, isolation 1) em 3 execuções espaçadas por 65 s;
  status HTTP 200:61, 201:2, 202:40, 204:5, 401:2, 404:12, nenhum 403/429/5xx. Os 2
  × 401 e 11 dos 404 são esperados (deslogado e isolamento entre usuários). Uma
  repetição às 22:59 identificou o 12º 404 (`POST /market-data/history/batch` em
  `/compare`; defeito do Dia 26, handoff H-22); nela o Docker caiu por falta de RAM
  (evento de ambiente, não regressão) e F9.2 e F9.3 não completaram.

**Achados corrigidos pelo E2E:** contraste do link "Ir para login" em `/portfolios`
(1,97:1 para 18,58:1) e balde de rate limit próprio para a telemetria (30/60 s por
IP; o limite de 30 do balde `standard` permanece), com aviso acessível para 429.

**Sem prova automatizada:** o CI do GitHub Actions está em `startup_failure` (135 de
135 execuções), anterior a esta branch. Pendências, inclusive as transferidas ao
Dia 29, em [DAY29_HANDOFF.md](docs/DAY29_HANDOFF.md).

Decisões de 2026-10-01 (decididas pelo usuário): exclusão de conta = anonimização
com D1–D5 (risco residual em `portfolio_events.note`; ADR da opção B obrigatória
antes de abrir o produto a outros usuários); artefatos de deploy saem do Dia 28 e
passam ao Dia 29. Decisões e pendências em
[PRODUCTION_RUNBOOK_DAY_28.md](docs/operations/PRODUCTION_RUNBOOK_DAY_28.md).

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
- Watchlist por usuário e heatmap por setor.
- Múltiplas carteiras próprias, ledger manual e cálculos factuais de posição, custo, patrimônio, P&L, rentabilidade, proventos e performance.
- Morning Call sem IA, inserido por comando interno e publicado após revisão humana.
- Testes essenciais, documentação, observabilidade e artefatos de deploy, sem publicação automática.

## Limites do produto

O produto não fornece gestão de carteira, compra/venda/manutenção, sinal, preço-alvo próprio, timing, alocação, suitability, promessa de resultado, execução em corretora ou orientação personalizada. Carteiras são registros informativos do usuário. Dados `DELAYED`, `EOD`, `DEMO` ou `STALE` nunca podem ser apresentados como tempo real/atual.

Stripe pode ser considerado no beta **somente em modo de teste**, isolado e opcional, no Dia 22 e mediante novo gate. Cobrança real, produção, assinatura comercial, paywall e planos pagos permanecem fora do escopo. Também não entram notificações, WhatsApp, Telegram, e-mail, push, IA, apps móveis, streaming tick a tick ou arquitetura de alta escala.

## Arquitetura resumida

- `apps/web`: Next.js App Router, React, TypeScript strict e Tailwind, a partir do Dia 2.
- `apps/api`: FastAPI, SQLAlchemy 2 e Alembic, a partir do Dia 2.
- Carteiras: ledger factual, append-only e isolado por usuário, com cálculos no domínio/backend.
- PostgreSQL/Neon compatível: fonte persistente.
- Redis/Upstash REST compatível: cache não autoritativo e locks.
- Refresh: processo curto/idempotente acionado futuramente por GitHub Actions cron contra endpoint interno protegido.
- Destinos pretendidos: Vercel para web e Render para API; nenhum serviço foi criado.

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
| [ADRs](docs/adr/) | Decisões arquiteturais aceitas |

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

## Verificações disponíveis no Dia 1

```powershell
git status --short --branch --untracked-files=all
git diff --check
python -m json.tool package.json
```

Build, lint, typecheck e testes de aplicação passam a existir após o scaffold. Verificação indisponível nunca deve ser descrita como aprovada.

## Contribuição e segurança

Leia [AGENTS.md](AGENTS.md), confirme o dia no [roadmap](docs/ROADMAP_30_DAYS.md), use Conventional Commits e preencha o [template de pull request](.github/PULL_REQUEST_TEMPLATE.md). Não faça push, deploy, login externo ou contratação sem autorização explícita.

Não publique credenciais, dados pessoais ou vulnerabilidades exploráveis. Consulte [SECURITY.md](SECURITY.md).

## Licença do repositório

O repositório não adota licença open source neste momento; consulte [LICENSE](LICENSE). Licença de código e licença de dados são assuntos separados.

## Próximo passo

Dia 29: GitHub Actions agendado para o endpoint interno protegido, acumulando as
pendências de [DAY29_HANDOFF.md](docs/DAY29_HANDOFF.md). Só começa com autorização
explícita.
