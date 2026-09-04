# Carteiras informativas — Dia 20

## Objetivo

O Dia 20 entrega o domínio mínimo de carteiras privadas informativas. Cada
usuário pode criar múltiplas carteiras, definir uma moeda-base imutável e
registrar manualmente eventos que são reaplicados de forma determinística para
reconstruir caixa e posições.

## Escopo implementado

- Carteiras privadas com isolamento por usuário.
- Moeda-base definida na criação e protegida contra alteração posterior.
- Ledger append-only com `CASH_DEPOSIT`, `CASH_WITHDRAWAL`, `BUY`, `SELL`,
  `FEE` e `REVERSAL`.
- Idempotência por `Idempotency-Key` e hash do payload.
- Replay usando `Decimal`, custo médio ponderado, posições e saldos de caixa.
- Reversão por novo evento, sem `UPDATE` ou `DELETE` de evento original.
- Rotas privadas versionadas em `/api/v1/portfolios` e cliente gerado por
  OpenAPI.
- Interface inicial acessível para criação, consulta de caixa, posições e
  ledger.

Todos os retornos permanecem factuais e informativos. A implementação não
calcula nem exibe valuation, P&L, TWR, rentabilidade, recomendação, suitability
ou ação de corretora. Também não ativa provider ou dado financeiro real.

## Regras de integridade

O domínio rejeita moeda incompatível, quantidade ou valor inválido, venda sem
posição suficiente e retirada sem caixa suficiente. Eventos são ordenados por
ocorrência e identificador para replay determinístico. A propriedade da
carteira é verificada em todas as rotas; recursos de outro usuário respondem
como inexistentes.

## Rotas

- `GET/POST /api/v1/portfolios`
- `GET/PATCH /api/v1/portfolios/{portfolio_id}`
- `POST/GET /api/v1/portfolios/{portfolio_id}/events`
- `POST /api/v1/portfolios/{portfolio_id}/events/{event_id}/reversal`
- `GET /api/v1/portfolios/{portfolio_id}/positions`
- `GET /api/v1/portfolios/{portfolio_id}/cash-balances`
- `GET /api/v1/portfolios/{portfolio_id}/summary`

## Próxima etapa

Valuation, P&L, TWR, rentabilidade, performance histórica e gráficos de
carteira permanecem fora do Dia 20 e só podem entrar após contrato, política,
proveniência e testes próprios.
