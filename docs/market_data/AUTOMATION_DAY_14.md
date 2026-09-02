# Automação operacional de mercado — Dia 14

Este documento descreve a operação local e agendada do refresh interno, o
backfill controlado e a reconciliação diária. Os artefatos são preparatórios:
nenhum provider real, dataset público ou credencial é ativado por este dia.

## Fluxo agendado

`.github/workflows/market-pulse-refresh.yml` executa a cada 15 minutos e também
aceita `workflow_dispatch`. O job chama somente o endpoint interno protegido
`POST /api/v1/internal/refresh-quotes`, usando os segredos
`MARKET_PULSE_API_BASE_URL` e `MARKET_PULSE_CRON_SECRET` configurados no GitHub
Actions. O payload versionado é `DRY_RUN` e usa uma identidade canônica
explícita; alterar para `DEMO_ONLY` ou `LICENSED_ONLY` exige revisão e gate
adicional. O workflow não imprime o segredo e não contém URL ou token fixo.

## Execução local

```powershell
$env:MARKET_PULSE_API_BASE_URL = "https://example.invalid"
$env:MARKET_PULSE_CRON_SECRET = "valor-ficticio"
python scripts/market_data_refresh.py equity.br.b3.petr4
python scripts/market_data_refresh.py --execute equity.br.b3.petr4
```

Sem `--execute`, o script apenas imprime o payload. O modo padrão é `DRY_RUN`;
identidades ticker-only, listas vazias ou mais de 100 itens são rejeitadas.

## Backfill controlado

`app.market_data.backfill` exige `canonical_ids`, limita cada execução a 100
instrumentos e 31 dias corridos, calcula um `run_id` determinístico e torna
repetições idempotentes. A decisão de licença ocorre antes da função provider;
por default o dataset é bloqueado, e `DEMO_SYNTHETIC` só é permitido para
fixtures locais. Cada sucesso invalida apenas a chave de histórico daquela
identidade, enquanto falhas de itens são reportadas como `PARTIAL`.

## Reconciliação diária

`app.market_data.reconciliation` compara dias úteis (com feriados fornecidos
explicitamente) com registros recebidos. Detecta gaps, provenance ausente,
quarentena e licença não aprovada sem transformar ausência em cotação. O
resultado é `COMPLETE`, `GAP` ou `BLOCKED`; fins de semana não geram falso gap.

## Runbook de falhas

- **Quota/provider indisponível:** manter o dataset bloqueado, registrar o
  `run_id` e servir somente snapshot validado `STALE`/`UNAVAILABLE`; não elevar
  limites nem trocar provider sem revisão documental.
- **Cold start/timeouts:** repetir com o mesmo `run_id` após o backoff; uma
  falha parcial não autoriza publicar itens sem provenance.
- **Backfill parcial ou sobreposto:** preservar itens concluídos, reexecutar a
  mesma janela/identidade e verificar invalidação granular; locks impedem
  sobreposição simultânea.
- **Quarentena/provenance ausente:** não publicar nem converter em dado real;
  corrigir a evidência na fonte e reconciliar novamente.
- **Rotação de segredo:** atualizar o segredo no ambiente de execução, testar
  manualmente com `workflow_dispatch` e revogar o valor anterior; nunca
  versionar o valor.

## Limites de segurança

O fluxo é operacional e factual. Não cria recomendação, sinal, suitability,
ordem, gestão de carteira ou promessa de retorno. `DEMO`, autenticação interna
e feature flags não concedem direitos de licença.
