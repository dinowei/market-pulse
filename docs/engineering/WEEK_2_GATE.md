# Gate da Semana 2 — dados, resiliência e operação

O gate fecha os Dias 8–14 e não autoriza provider real, deploy, cobrança ou
avanço automático. A aprovação depende de evidência reproduzível localmente.

## Critérios objetivos

- Catálogo mestre e P0 operacional mantêm `canonical_id` estável e estados de
  cobertura separados.
- Adapters e normalização preservam Decimal, timezone, DataLevel, Freshness e
  provenance; default deny bloqueia datasets não aprovados.
- Eventos corporativos permanecem append-only e não creditam carteiras
  automaticamente.
- Cache-aside, stale-if-error, locks e refresh interno têm testes de
  idempotência, falha parcial e invalidação granular.
- Backfill do Dia 14 é limitado, auditável e bloqueado antes da chamada do
  provider quando a licença não foi aprovada.
- Reconciliação diária detecta gaps e provenance ausente, ignorando fins de
  semana e feriados explicitamente configurados.
- Workflow agendado e `workflow_dispatch` usam apenas referências a secrets;
  nenhum segredo, URL fixa ou provider real está no repositório.
- Migrations up/down/up, Pytest, Ruff, lint/typecheck/test/build web,
  OpenAPI, health checks, secret scan e `git diff --check` passam.

## Evidências e bloqueios

O relatório do gate deve registrar comandos, exit codes, `run_id`s, resultados
de `/health/live` e `/health/ready`, estado do Compose e árvore Git final.
Qualquer falha de licença, provenance, segurança, migration ou contrato bloqueia
o gate; não se contorna removendo testes ou relaxando o default deny.
