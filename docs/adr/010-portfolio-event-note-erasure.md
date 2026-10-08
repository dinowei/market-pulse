# ADR-010: Anulação de `portfolio_events.note` na anonimização de conta (opção B)

- Status: Accepted
- Data: 2026-10-05
- Decisores: responsável técnico (Claude Code), com delegação explícita do operador do
  projeto para os itens do Dia 30 (H-08)
- Relação: resolve o risco residual D3-A do
  [runbook do Dia 28](../operations/PRODUCTION_RUNBOOK_DAY_28.md), §4.2; não altera a
  ADR-007 (ledger append-only), apenas restringe a única exceção.

## Contexto

A exclusão de conta é anonimização (decisões D1–D5, 2026-10-01). O ledger
`portfolio_events` é append-only, garantido pela trigger
`prevent_immutable_portfolio_event_change`, que recusa todo `UPDATE` e `DELETE`. A coluna
`note` é texto livre digitado pelo usuário e pode conter dado pessoal; por isso ficava
fora da anonimização. Isso foi aceito só para o beta fechado (opção A), com esta ADR
obrigatória antes de abrir o produto a outras pessoas.

## Decisão

Opção **B**: a trigger passa a aceitar **exatamente uma** forma de `UPDATE`, que leva
`note` de um valor não nulo para `NULL` sem mudar nenhuma outra coluna. Todo o resto
continua recusado: `DELETE`, alteração de valores, reescrita da nota e anulação da nota
junto com outra coluna.

- A comparação usa a linha inteira em JSONB menos `note`
  (`to_jsonb(NEW) - 'note' = to_jsonb(OLD) - 'note'`). Assim a regra continua correta para
  colunas criadas no futuro, sem lista manual de colunas.
- `DELETE /api/v1/account` anula as notas de todos os eventos das carteiras do usuário
  na mesma transação da anonimização, antes da linha de auditoria.
- Migration `20261005_0012`. O downgrade restaura a trigger original; notas já anuladas
  continuam nulas, porque o texto foi apagado de propósito e não é recuperável.

## Alternativas consideradas

- **A (manter a nota):** rejeitada para a abertura do produto, pelo risco de dado pessoal.
- **C (cifrar notas com chave por usuário e destruir a chave):** mais flexível, mas exige
  gestão de chaves; fica como evolução futura se as notas precisarem ser preservadas para
  o próprio usuário.

## Consequências positivas

- Nenhum texto livre do usuário sobrevive à anonimização no ledger.
- Valores, datas, moedas, ids e vínculos do ledger continuam imutáveis, provados por teste.

## Consequências negativas e riscos

- `idempotency_key` também é definido pelo cliente e continua imutável; o risco é menor
  porque o frontend gera esse valor, e fica registrado como residual.
- A trigger agora tem uma ramificação; qualquer mudança futura nela exige teste contra
  banco real.

## Evidência

- Migration aplicada, revertida e reaplicada no Postgres de teste (`market_pulse_test`,
  2026-10-05). Na mesma execução: anulação permitida; alteração de valor, reescrita da
  nota, anulação com outra coluna, `NULL` para `NULL` e `DELETE` recusados. Todas as
  linhas de verificação foram desfeitas por rollback.
- Testes: `tests/test_account_anonymization_day28.py` (fluxo sem infraestrutura e teste
  opt-in de ponta a ponta em banco descartável, que roda na Rodada 1, etapa E12).
