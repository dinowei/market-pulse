# Operação do endpoint interno de refresh

O serviço foi desenhado para um processo curto e sob demanda, preservando
baixo custo operacional em vez de manter um worker contínuo. Um cron externo
futuro deverá usar o segredo configurado no ambiente do serviço e enviar apenas
um lote explícito, por exemplo:

```text
X-Cron-Secret: local_demo_only_change_me
X-Request-ID: <uuid-v4>
```

O placeholder acima é demonstrativo e não deve ser reutilizado em produção.

Antes de permitir `LICENSED_ONLY`, cada combinação provider/plano/endpoint/
dataset/finalidade/modalidade/ambiente precisa estar aprovada na matriz de
licenças. O endpoint falha fechado sem configuração, mantém `run_id` para
correlação, usa locks owner-only e não usa `FLUSHALL`. Repetições são
idempotentes por identidade de job; falhas individuais tornam o resultado
`PARTIAL` sem esconder o diagnóstico sanitizado.

O modo `DEMO_ONLY` é exclusivamente sintético e permanece marcado como DEMO.
Nenhum caminho deste documento autoriza login externo, provider real, cobrança,
recomendação financeira ou deploy.
