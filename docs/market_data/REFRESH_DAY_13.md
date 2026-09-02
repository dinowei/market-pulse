# Refresh de mercado — Dia 13

O endpoint `POST /api/v1/internal/refresh-quotes` é uma operação interna para
acionamento futuro por cron/GitHub Actions. Ele não é usado pela interface do
usuário e não aceita sessão, cookie ou Bearer token como autorização.

## Autorização e configuração

O chamador deve enviar `X-Cron-Secret`. O valor é comparado com
`MARKET_PULSE_INTERNAL_REFRESH_SECRET` por `secrets.compare_digest`. Sem
segredo configurado, com header ausente ou incorreto, a resposta é um Problem
Details 401 genérico e nenhuma operação de refresh é iniciada. O `.env.example`
contém apenas um valor vazio; nunca coloque segredo real no Git.

## Payload e limites

O corpo estrito contém `dataset`, `capability`, `canonical_ids`, `mode` e
`max_items` opcional. A lista deve ser explícita, não vazia, sem duplicatas e
respeitar `MARKET_PULSE_REFRESH_MAX_ITEMS` (20 por padrão). Os modos são
`DEMO_ONLY`, `LICENSED_ONLY` e `DRY_RUN`; o último não chama provider nem grava
dados.

## Execução segura

Cada chamada recebe `run_id` e preserva o `X-Request-ID` (ou o ID gerado pelo
middleware). Cada instrumento reutiliza o refresh idempotente do Dia 12.1,
obtém lock com TTL e invalida somente o cache relacionado após sucesso.
Licenciamento é avaliado antes de qualquer provider; fontes não aprovadas são
contabilizadas como `skipped` e não são chamadas. `DemoProvider` só é usado no
modo `DEMO_ONLY`, em ambiente local/teste, e retorna sempre `DataLevel.DEMO`.

Falhas por item são contabilizadas sem interromper o lote. O resumo informa
`SUCCESS`, `PARTIAL`, `FAILED` ou bloqueio/indisponibilidade, além de itens
processados, falhos, ignorados, quarentenados e invalidações de cache. Erros,
headers, URLs e payloads brutos não são retornados nem registrados.

O endpoint não ativa provider real, não concede licença, não usa dado real e
não substitui o futuro fluxo de persistência/auditoria de produção.
