# ADR-002: Atualização recorrente por acionador externo

- Status: Accepted
- Data: 2026-08-30
- Decisores: operador do projeto e responsável técnico

## Contexto

Dados precisam de atualização, mas um daemon permanente adiciona supervisão e custo. A arquitetura aprovada também exige processo separado que compartilhe o código da API.

## Decisão

Usar futuramente scheduler externo/gerenciado para iniciar um job curto e idempotente construído com o mesmo código da API. O job é processo separado, não worker residente. No Dia 1 não há cron, endpoint nem serviço configurado.

Frequência, backoff, concorrência, idempotência e alertas serão fechados após interface manual e primeiro adapter validado.

## Alternativas consideradas

- Worker permanente: flexível, mas exige supervisão.
- Scheduler dentro da API: simples, mas duplica execução em réplicas.
- Cron externo + job curto: separa acionamento e execução com menor operação.

## Consequências positivas

- Sem daemon ocioso.
- Execução manual e recorrente compartilham caminho.
- Scheduler pode ser trocado.

## Consequências negativas e riscos

- Dependência de plataforma futura.
- Autenticação do acionamento e replay exigem cuidado.
- Limites de duração podem restringir providers.

## Como revisar esta decisão

Revisar após medir duração, volume, frequência e falhas; considerar worker residente apenas com necessidade demonstrada.
