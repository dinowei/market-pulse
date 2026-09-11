# Dia 26 — Comparação multiativo, benchmarks e calendário econômico

Este documento registra o contrato e os gates do Dia 26. Ele não autoriza
provider externo, dado financeiro real, redistribuição ou alteração do
licenciamento `default deny`.

## Entregáveis

- `POST /api/v1/market-data/quotes/batch` e
  `POST /api/v1/market-data/history/batch` aceitam até dez `canonical_id`
  únicos.
- O histórico oferece `PRICE` e `INDEX_100`. O índice é calculado somente
  com `Decimal`, com base no primeiro ponto disponível, e preserva preço bruto,
  gaps, timestamps e fallback tabular.
- `GET /api/v1/market-data/benchmarks` expõe somente o universo fixo do beta:
  Ibovespa, CDI, IPCA, IFIX, USD/BRL, S&amp;P 500 e Nasdaq. Os itens são
  sintéticos, `DataLevel=DEMO`, com fonte e limitações explícitas.
- `GET /api/v1/economic-calendar` e
  `GET /api/v1/economic-calendar/{event_id}` expõem eventos factuais, com
  importância, status, valores, país, timezone IANA e provenance. O intervalo
  solicitado não pode exceder 366 dias.
- Textos de eventos passam por bloqueio lexical de termos prescritivos ou de
  sinal. O contrato não possui campos de recomendação, ação, sinal ou alvo.
- O frontend usa apenas tipos gerados do OpenAPI, visualiza múltiplas séries
  em `INDEX_100` por padrão, permite `PRICE`, mantém valores reais na tabela e
  mostra fallback acessível, provenance, `DataLevel` e `Freshness`.

## Limitações e segurança

Todos os dados do Dia 26 são DEMO e não representam cotação, índice, previsão
ou calendário oficial. `DEMO`, feature flag, autenticação interna ou acesso
administrativo não concedem licença. A futura troca por provider aprovado exige
novo gate documental, verificação de cobertura/licença e preservação de
`source`, timestamps, `DataLevel`, `Freshness` e limitações.

## Validação reproduzível

```powershell
python -m uv run --directory apps/api pytest -q tests/test_day26_multiativo_calendar.py
python -m uv run --directory apps/api ruff check app tests
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
python -m uv run --directory apps/api python ../../scripts/day26_compliance.py
python scripts/week1_gate.py secrets
python scripts/week1_gate.py supply-chain
git diff --check
```

O workflow `.github/workflows/day26-compliance.yml` repete os gates sem rede de
provider e falha se encontrar tokens proibidos, termos prescritivos no payload
de DEMO ou tipos financeiros de ponto flutuante nos módulos do Dia 26.
