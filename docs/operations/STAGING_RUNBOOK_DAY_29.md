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
| PostgreSQL | Render Postgres grátis 16, banco `market_pulse_staging`, sem acesso externo | Expira **30 dias após a criação**, 1 GB, sem backup, um por workspace ([free](https://render.com/docs/free)). Nunca o banco `market_pulse_test` da suíte (`conftest` faz `TRUNCATE`). |
| Cron | Nenhum | Decisão C4 no H-05; refresh manual. |

O navegador fala só com a origem do web; `/api/v1/*` é repassado para a API (ADR-008).

**Atualização de 2026-10-05:** a infraestrutura do Render é declarada em
[`render.yaml`](../../render.yaml) (Blueprint). O Render cria banco, Key Value e API, liga
`MARKET_PULSE_DATABASE_URL` e `MARKET_PULSE_REDIS_URL` por referência e gera
`MARKET_PULSE_INTERNAL_REFRESH_SECRET`. Nenhuma credencial passa por arquivo, chat ou
terminal. Isso substitui o Neon e a migration manual previstos na primeira versão deste
runbook.

## 2. Pré-requisitos

1. Branch `feature/dia-29-staging` no GitHub (feito em 2026-10-05).
2. **[VOCÊ]** Contas no Render e na Vercel. Não informe credenciais no chat.
3. Rodadas oficiais (PowerShell, `C:\Projetos\mp-local-check`) verdes no commit a implantar.

## 3. Aplicar o Blueprint e migrations

1. **[VOCÊ]** Render → New → Blueprint → Public Git Repository
   `https://github.com/dinowei/market-pulse`, branch `feature/dia-29-staging`.
   Conectar pelo repositório público dispensa dar acesso ao app do Render no GitHub, mas
   desliga o auto-deploy: cada deploy é disparado manualmente.
2. **[VOCÊ]** Preencher `MARKET_PULSE_CORS_ORIGINS` com a origem de produção do projeto
   Vercel em JSON (exemplo de formato: `["https://<projeto>.vercel.app"]`) e aplicar.
3. **Migrations:** rodam no comando de start (`alembic upgrade head` antes do uvicorn),
   porque o pre-deploy command não existe na instância grátis
   ([deploys](https://render.com/docs/deploys)). Com uma única instância não há corrida;
   quando o schema já está em head, o comando não faz nada e só acrescenta alguns
   segundos ao cold start.

## 4. Render — API

| Campo | Valor |
|---|---|
| Runtime | Python 3 nativo |
| Root Directory | `apps/api` ([monorepo-support](https://render.com/docs/monorepo-support)) |
| Build command | `uv sync --frozen --no-dev` (validado em 2026-10-06) |
| Start command | `uv run --frozen --no-dev alembic upgrade head && uv run --frozen --no-dev uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-proxy-headers` (validado em 2026-10-06; `--no-proxy-headers` pela ADR-012) |
| Health check path | `/health/live` |
| Key Value | `noeviction`: memória cheia gera erro (503, falha fechada) em vez de apagar sessões, revogações ou contadores |

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
| `MARKET_PULSE_DATABASE_URL` | Ligada pelo Blueprint (`fromDatabase`). |
| `MARKET_PULSE_REDIS_URL` | Ligada pelo Blueprint (`fromService`, URL **interna**; a externa fica desabilitada). |
| `MARKET_PULSE_INTERNAL_REFRESH_SECRET` | Gerada pelo Render (`generateValue`). |
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
| Deployment Protection | Recomendado: Vercel Authentication também em produção (disponível no Hobby, [hobby](https://vercel.com/docs/plans/hobby)). **Medido em 2026-10-06:** só os previews estão protegidos; o domínio de produção responde sem login. O cadastro fechado impede contas novas, mas a interface fica visível a quem tiver a URL. Ligar a proteção é decisão do usuário |

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
6. Sem provider `PUBLIC_APPROVED`, nenhum dado de mercado aparece como real: só dados
   sintéticos rotulados `DEMO`/`STALE` (contrato do Dia 15) ou `UNAVAILABLE` (H-12).
7. Redeploy da API sem erro 5xx no log durante a troca de instância (shutdown pelo SIGTERM).

### Resultado do smoke em 2026-10-06 (MEDIDO por Claude Code)

Ambiente: web `https://market-pulse-staging.vercel.app` (projeto Vercel `market-pulse`,
produção na branch `feature/dia-29-staging`, build `b7b3433`); API
`https://market-pulse-staging-api.onrender.com` (Blueprint `market-pulse-staging`).

| Item | Resultado |
|---|---|
| 1 | `/health/live` 200; `/health` 200 com `environment: staging`; `/health/ready` 200 com banco e cache `ok` |
| 2 | `/docs`, `/redoc` e `/openapi.json` → 404 |
| 3 | `GET <web>/api/v1/instruments` → 200 pelo proxy, com `X-Request-Id` e os cabeçalhos de segurança da API |
| CSRF pelo proxy | login com o `Origin` do web → 401 (credencial fictícia, sem `Set-Cookie`); `Origin` forjado → 403. O proxy repassa o `Origin` (parte do **[A VALIDAR]** da ADR-008) |
| Cadastro | `POST /api/v1/auth/register` → 404, direto e pelo proxy |
| 4 e 5 | **PENDENTE:** exigem a conta única (§6), criada pelo usuário. O repasse do cookie de sessão pelo proxy segue **[A VALIDAR]** |
| 6 | A página inicial mostra PETR4 com dados **sintéticos rotulados** `DEMO`/`STALE` e o aviso de que não representam cotação real. Nenhum dado se apresenta como real. A limitação dizia "Demonstração local", texto corrigido na branch do Dia 30 |
| 7 | Três trocas de instância (deploys e o sono do plano grátis) com `Shutting down` → `Application shutdown complete` em cerca de 100 ms e **zero** respostas 5xx desde o primeiro deploy bem-sucedido |
| Migrations | `alembic upgrade head` no boot aplicou 0001 → 0011 no banco do staging |
| Forja de IP | `X-Forwarded-For` forjado virava o IP do cliente; com `--no-proxy-headers` passou a `127.0.0.1` (ADR-012) |
| Cadastro com 422 (2026-10-06) | Tentativas reais do usuário recusadas com 422: a senha exige 12+ caracteres com letras e números, e o formulário não dizia isso. **Corrigido** no commit `60df9ca`: a regra aparece no campo, há validação antes do envio e uma mensagem por status. Medido no ar em `/register` |

## 8. Rollback

- **API ou web:** reimplantar o deployment anterior pelo painel da plataforma.
- **Schema:** seguir o procedimento de rollback de migrations registrado no
  [runbook do Dia 28](PRODUCTION_RUNBOOK_DAY_28.md), §4, sempre num banco de staging.
- **Vazamento suspeito:** rotacionar `MARKET_PULSE_INTERNAL_REFRESH_SECRET` e as credenciais
  do banco nos painéis (runbook do Dia 28, §2).
