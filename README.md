# Market Pulse

O Market Pulse é um terminal web autenticado para acompanhamento **informativo e analítico** de mercados financeiros e carteiras próprias. O beta de 30 dias terá universo aprovado de ativos, dashboard, busca/páginas de ativo, Particle Atlas acessível, Global Atlas tabular, watchlist, carteiras informativas, heatmap setorial, cotações com proveniência e freshness e Morning Call inserido por comando administrativo.

> **Conteúdo informativo. Não constitui recomendação de investimento.**

## Status atual

O repositório possui a implementação até o **Dia 24**, incluindo autenticação,
watchlists, carteiras, Morning Call e uma demonstração local persistida,
determinística e isolada. O Dia 24 foi validado com PostgreSQL e Redis locais,
migrations, reset/seed do banco DEMO e E2E de fluxo principal e isolamento entre
usuários. Nenhum provider real, Stripe ou deploy foi ativado por esta etapa.

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

O **Dia 24** está concluído localmente. O Dia 25 entrega o painel operacional
interno documentado em [ADMIN_SYSTEM_DAY_25.md](docs/operations/ADMIN_SYSTEM_DAY_25.md).
