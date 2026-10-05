# Market Pulse — runbook do staging privado (Dia 29)

- **Data:** 2026-10-05
- **Escopo:** staging **privado**, com acesso de um único usuário, conforme a
  reconciliação do Dia 29 em [ROADMAP_30_DAYS.md](../ROADMAP_30_DAYS.md).
- **Este runbook não autoriza** criação de conta, login, contratação, push nem deploy.
  Cada um desses atos é feito pelo usuário, com autorização explícita por conta e serviço.
- **Decisões:** [ADR-008](../adr/008-same-origin-api-proxy.md) (proxy same-origin) e
  pendências em [DAY29_HANDOFF.md](../DAY29_HANDOFF.md).

Legenda: **[VOCÊ]** = passo do usuário em painel externo; **[A VALIDAR]** = depende de
comportamento de plataforma não confirmado na documentação oficial consultada.

## 1. Arquitetura do staging

| Peça | Plataforma | Observação |
|---|---|---|
| Web (Next.js 16) | Vercel Hobby, Root Directory `apps/web` | Build nativo, sem Dockerfile ([nextjs](https://vercel.com/docs/frameworks/full-stack/nextjs), [monorepos](https://vercel.com/docs/monorepos)). Uso pessoal e não comercial ([hobby](https://vercel.com/docs/plans/hobby)). |
| API (FastAPI) | Render web service grátis, runtime Python nativo, Root Directory `apps/api` | Sem Dockerfile ([deploy-fastapi](https://render.com/docs/deploy-fastapi)). Dorme após 15 min sem tráfego e volta em cerca de 1 min ([free](https://render.com/docs/free)). |
| Redis | Render Key Value grátis, **mesma região** da API | Sem persistência ([key-value](https://render.com/docs/key-value)); decisão R2 no H-03. |
| PostgreSQL | Neon, **banco próprio do staging** | Nunca o banco `market_pulse_test` nem o branch usado pela suíte (`conftest` faz `TRUNCATE`). |
| Cron | Nenhum | Decisão C4 no H-05; refresh manual. |

O navegador fala só com a origem do web; `/api/v1/*` é repassado para a API (ADR-008).

## 2. Pré-requisitos

1. **[VOCÊ]** Autorizar o push da branch que será implantada. Vercel e Render implantam a
   partir do GitHub; sem push não há deploy.
2. **[VOCÊ]** Criar as contas e os recursos (Vercel, Render, banco Neon do staging). Não
   informe credenciais no chat: elas vão direto nos painéis.
3. Rodadas oficiais (PowerShell, `C:\Projetos\mp-local-check`) verdes no commit a implantar.

## 3. Banco do staging e migrations

O pre-deploy command do Render não existe na instância grátis
([deploys](https://render.com/docs/deploys)). **Decisão:** migrations são um passo manual,
explícito e anterior a cada deploy que mude o schema. Não vão no comando de start, para não
rodar a cada wake-up nem em paralelo.

1. **[VOCÊ]** Criar no Neon um banco dedicado (sugestão: `market_pulse_staging`).
2. **[VOCÊ]** No PowerShell, em `apps/api`, definir `MARKET_PULSE_DATABASE_URL` **só na
   sessão do terminal** (nunca em arquivo versionado) e rodar
   `.\.venv\Scripts\python.exe -m alembic upgrade head`.
   O `migrations/env.py` lê exatamente essa variável.
3. Fechar o terminal ao terminar, para descartar a variável.

## 4. Render — API

| Campo | Valor |
|---|---|
| Runtime | Python 3 nativo |
| Root Directory | `apps/api` ([monorepo-support](https://render.com/docs/monorepo-support)) |
| Build command | `uv sync --frozen --no-dev` **[A VALIDAR]** |
| Start command | `uv run --frozen --no-dev uvicorn app.main:app --host 0.0.0.0 --port $PORT` **[A VALIDAR]** |
| Health check path | `/health/live` |

- O Render inclui o `uv` quando há `uv.lock` na raiz do projeto
  ([uv-version](https://render.com/docs/uv-version)); o `uv.lock` está em `apps/api`.
  Os comandos exatos de build e start com `uv` não aparecem na fonte oficial: se o build
  falhar, registre a saída e ajuste antes de seguir.
- O health check usa `/health/live`, que não depende de DB nem de Redis. O
  `/health/ready` devolve 503 quando o Redis grátis reinicia, e o Render reinicia a
  instância após 60 s de falha ([health-checks](https://render.com/docs/health-checks)).
- O Render envia SIGTERM e, após o shutdown delay (padrão 30 s), SIGKILL
  ([deploys](https://render.com/docs/deploys)). O encerramento limpo do uvicorn é
  verificado no smoke do item 7.

### Variáveis de ambiente da API (nomes; valores só no painel)

| Nome | Regra |
|---|---|
| `PYTHON_VERSION` | `3.11.9`, a versão local testada. Sem ela, um serviço novo usa 3.14.x ([python-version](https://render.com/docs/python-version)). |
| `MARKET_PULSE_ENVIRONMENT` | `staging` (ativa a validação estrita). |
| `MARKET_PULSE_DATABASE_URL` | URL do banco do staging. |
| `MARKET_PULSE_REDIS_URL` | **URL interna** do Key Value. A externa vem desabilitada por padrão. |
| `MARKET_PULSE_INTERNAL_REFRESH_SECRET` | Aleatório, com 16 caracteres ou mais. |
| `MARKET_PULSE_CORS_ORIGINS` | JSON com **só** a origem de produção do projeto Vercel. |
| `MARKET_PULSE_DEMO_ENABLED` | `false`; `true` é recusado no boot. |
| `MARKET_PULSE_AUTH_COOKIE_SECURE` | `true`. O login já força `Secure` fora de `local`/`test`; deixar explícito. |
| `MARKET_PULSE_AUTH_COOKIE_SAMESITE` | `lax`; `none` é recusado no boot (ADR-008). |
| `MARKET_PULSE_REGISTRATION_ENABLED` | Vazio ou `false`. Ver o item 6. |

**Não definir no staging:** `MARKET_PULSE_TEST_*`, `MARKET_PULSE_DEMO_DATABASE_URL`,
`MARKET_PULSE_DEMO_ALLOW_RECREATE`, `APP_ENV` e qualquer chave de provider. As demais
variáveis `MARKET_PULSE_*` têm padrão no código.

## 5. Vercel — web

| Campo | Valor |
|---|---|
| Root Directory | `apps/web` |
| Framework | Next.js (detecção automática) |
| Deployment Protection | Vercel Authentication ligada (disponível no Hobby, [hobby](https://vercel.com/docs/plans/hobby)) |

### Variáveis de ambiente do web

| Nome | Regra |
|---|---|
| `MARKET_PULSE_API_PROXY_ORIGIN` | Origem `https` da API no Render, sem caminho. Valor inválido falha o build. |
| `NEXT_PUBLIC_API_BASE_URL` | A **própria** origem de produção do projeto Vercel. É embutida no build: mudar exige redeploy ([environment-variables](https://vercel.com/docs/environment-variables)). |

A origem de produção da Vercel só é conhecida depois do primeiro deploy: faça o deploy,
defina as duas variáveis e `MARKET_PULSE_CORS_ORIGINS` no Render, e então refaça os deploys.

## 6. Conta única do staging

O cadastro é **fechado por padrão** em `staging`/`production` (`registration_open`, H-11):
`POST /api/v1/auth/register` devolve 404.

1. **[VOCÊ]** Definir `MARKET_PULSE_REGISTRATION_ENABLED=true` no Render e redeployar.
2. **[VOCÊ]** Criar a sua conta em `/register`.
3. **[VOCÊ]** Voltar a variável para vazio ou `false` e redeployar **imediatamente**.
4. Confirmar que um novo `POST /api/v1/auth/register` devolve 404.

## 7. Smoke do staging (registrar saída e data)

1. `GET <api>/health/live` → 200.
2. `GET <api>/docs`, `/redoc` e `/openapi.json` → 404.
3. `GET <web>/api/v1/instruments` → 200, passando pelo proxy.
4. Login em `<web>/login`; depois `/watchlists` carrega autenticado, sem 401. Isso
   prova o cookie first-party pelo proxy (**[A VALIDAR]** da ADR-008).
5. Logout; depois `/watchlists` mostra o estado sem sessão.
6. Sem provider `PUBLIC_APPROVED` e sem DEMO, os dados de mercado aparecem como
   `UNAVAILABLE` explícito, nunca como cotação inventada (decisão do H-12).
7. Redeploy da API sem erro 5xx no log durante a troca de instância (shutdown pelo SIGTERM).

## 8. Rollback

- **API ou web:** reimplantar o deployment anterior pelo painel da plataforma.
- **Schema:** seguir o procedimento de rollback de migrations registrado no
  [runbook do Dia 28](PRODUCTION_RUNBOOK_DAY_28.md), §4, sempre num banco de staging.
- **Vazamento suspeito:** rotacionar `MARKET_PULSE_INTERNAL_REFRESH_SECRET` e as credenciais
  do banco nos painéis (runbook do Dia 28, §2).
