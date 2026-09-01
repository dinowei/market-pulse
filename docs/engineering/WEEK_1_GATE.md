# Gate da Semana 1

Este gate fecha a fundação, contratos, schema, providers, CI e supply chain antes do avanço para a Semana 2. Ele não autoriza provider financeiro real, Stripe, recomendação ou deploy.

## Pré-condições

- Workspace na raiz do repositório, branch de trabalho revisada e árvore limpa.
- Node compatível com o manifesto (`>=24.20.0 <25`; CI usa Node 24) e Python 3.11+.
- Docker Desktop Linux apenas para validação local; GitHub Actions usa serviços nativos.
- `.env.example` contém somente nomes/valores demonstrativos.

## Gate local — Windows PowerShell

```powershell
pnpm install --frozen-lockfile
python -m uv sync --project apps/api --group dev
python scripts/week1_gate.py supply-chain
python scripts/week1_gate.py secrets
pnpm --filter @market-pulse/web lint
pnpm --filter @market-pulse/web typecheck
pnpm --filter @market-pulse/web test
pnpm --filter @market-pulse/web build
docker compose up -d postgres redis
$env:PYTHONPATH='apps/api'
python -m uv run --directory apps/api alembic upgrade head
python -m uv run --directory apps/api alembic downgrade base
python -m uv run --directory apps/api alembic upgrade head
python -m uv run --directory apps/api ruff check apps/api/app apps/api/tests
python -m uv run --directory apps/api pytest
python -m json.tool docs/api/openapi.json > $null
docker compose down
```

## Gate local — Linux/macOS

```bash
pnpm install --frozen-lockfile
python -m uv sync --project apps/api --group dev
python scripts/week1_gate.py supply-chain
python scripts/week1_gate.py secrets
pnpm --filter @market-pulse/web lint && pnpm --filter @market-pulse/web typecheck
pnpm --filter @market-pulse/web test && pnpm --filter @market-pulse/web build
docker compose up -d postgres redis
PYTHONPATH=apps/api python -m uv run --directory apps/api alembic upgrade head
PYTHONPATH=apps/api python -m uv run --directory apps/api alembic downgrade base
PYTHONPATH=apps/api python -m uv run --directory apps/api alembic upgrade head
python -m uv run --directory apps/api ruff check apps/api/app apps/api/tests
python -m uv run --directory apps/api pytest
python -m json.tool docs/api/openapi.json >/dev/null
docker compose down
```

## CI e contratos

O workflow executa instalação congelada, lint/typecheck/test/build web, Ruff/Pytest, migrations com PostgreSQL/Redis de serviço, JSON OpenAPI, sincronização do cliente gerado, testes de default deny/imutabilidade/idempotência e os scripts de segredo/supply chain. O cliente é regenerado em diretório temporário e comparado; nenhuma mudança pública deve ser silenciosa.

## Banco, cache e falhas

`/health/live` deve responder 200. `/health/ready` deve responder 200 quando PostgreSQL e Redis estiverem saudáveis. Falha de migration, serviço, contrato, segredo, licença ou regra financeira bloqueia a Semana 2; não contorne o erro removendo o teste.

## Supply chain e SBOM

Lockfiles são obrigatórios. `pnpm audit` é executado quando disponível; resultados exigem revisão de severidade. A checagem de licenças imprime relatório e marca desconhecidos para revisão manual, sem aprovar por inferência. SBOM fica P1 operacional: adotar CycloneDX ou Syft quando houver necessidade de distribuição/produção e registrar o artefato versionado.

## CodeQL

CodeQL não é habilitado no Dia 7 porque o repositório ainda não possui build matrix ou política de retenção para análise pesada. O CI mantém Ruff, TypeScript, ESLint, secret scan e validações de contrato; CodeQL é critério P1 quando houver código de produção e workflow dedicado.
