# Dia 27 — rollback seguro de eventos corporativos

## Decisão

A migração `20260902_0004_corporate_actions_pipeline` precisa continuar
reversível mesmo quando `corporate_actions` já contém linhas. O downgrade
preenche `effective_date` usando, nesta ordem determinística, `ex_date`,
`payment_date`, `record_date`, `announced_date`, `declared_date` e, como último
recurso documentado, `created_at::date`. `source_timestamp` usa o valor
existente, depois `created_at` e `updated_at`. Linhas não são removidas e os
valores monetários/razões legados são preservados antes da remoção das colunas
introduzidas pela migração.

## Gate isolado

O teste opt-in
`apps/api/tests/test_corporate_actions_migration_regression.py` executa
upgrade, insere uma ação corporativa sintética, faz upgrade até `head`,
downgrade até `20260901_0003` e upgrade novamente. Ele só aceita uma URL local
para o banco dedicado `market_pulse_migration_test` e exige
`MARKET_PULSE_MIGRATION_REGRESSION=true`; qualquer outro alvo falha fechado.

Execução local:

```powershell
$env:MARKET_PULSE_MIGRATION_REGRESSION='true'
$env:MARKET_PULSE_MIGRATION_DATABASE_URL='postgresql://<local>/market_pulse_migration_test'
python -m uv run --project apps/api pytest -q apps/api/tests/test_corporate_actions_migration_regression.py -rs
```

O workflow `.github/workflows/demo-integration.yml` cria o banco efêmero
separado e executa o mesmo teste. O banco principal e o banco de demonstração
não são alvos desse reset/regressão.

## Evidência do Dia 27

O E2E `apps/web/e2e/demo.spec.ts` falhava com `404` apenas quando executado
contra um banco local sem seed. Com `market_pulse_demo` resetado e semeado pelo
serviço oficial, as rotas passaram; o instrumento `demo.equity.mpxa3` já faz
parte do seed determinístico. A integridade referencial dos marcadores e a
telemetria sem PII permanecem cobertas por
`apps/api/tests/test_day27_income_markers_telemetry.py`.

TradingView Lightweight Charts não está integrado. A decisão permanece adiada
até que `Decimal`, `DataLevel`, `Freshness` e proveniência possam ser
preservados sem conversão implícita para `float`.
