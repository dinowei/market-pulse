# Market Pulse API — instruções locais

Estas regras complementam `AGENTS.md` da raiz e `docs/engineering/ENTERPRISE_ENGINEERING_BASELINE.md`.

## Leitura obrigatória

Antes de alterar a API, leia integralmente:

- `../../AGENTS.md`;
- `../../docs/engineering/ENTERPRISE_ENGINEERING_BASELINE.md`;
- `../../docs/PROJECT_SPEC.md`;
- `../../docs/ARCHITECTURE.md`;
- `../../docs/policies/FINANCIAL_CONTENT_POLICY.md`;
- ADRs e OpenAPI aplicáveis.

Sempre que a tarefa envolver cotações, histórico, FX, dados de mercado, providers, carteiras, rentabilidade, P&L, TWR, gráficos financeiros, Morning Call ou exibição de preço, leia docs/policies/FINANCIAL_DATA_AND_PORTFOLIO_INTEGRITY_POLICY.md antes de alterar arquivos.

## Regras locais

- Preserve o monólito modular e os limites de domínio; não acople providers ao domínio.
- Rotas públicas usam `/api/v1`, Problem Details e `X-Request-ID` conforme a baseline.
- Use SQLAlchemy 2, Alembic e tipos decimais para valores financeiros; não use floats financeiros.
- Não altere migrations existentes; novas migrations devem ser revisáveis e acompanhadas de testes.
- Providers reais, segredos, deploy, push e integrações externas exigem autorização explícita.
