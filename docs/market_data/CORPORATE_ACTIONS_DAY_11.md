# Eventos corporativos — Dia 11

Este documento descreve a ingestão, normalização e reconciliação auditável de eventos corporativos sintéticos ou provenientes de datasets que venham a ser aprovados. Nenhum provider real é ativado neste dia e nenhum evento é aplicado automaticamente a carteiras de usuários.

## Tipos suportados

- `CASH_DIVIDEND`: dividendo em dinheiro por ação/cota.
- `JCP`: juros sobre capital próprio por ação/cota.
- `SPLIT`: desdobramento, com quantidade econômica equivalente.
- `REVERSE_SPLIT`: grupamento, com quantidade econômica equivalente.

## Campos e datas

Todo evento identifica `instrument_id`/`canonical_id`, `provider`, `dataset`, `external_id` quando disponível, `external_event_key`, `action_type`, `status`, `source_timestamp` ou `collected_at`, além de `ingestion_batch_id` e `raw_payload_record_id` quando persistido.

As datas têm significados distintos:

- `announced_date`: anúncio público do evento;
- `ex_date`: primeiro dia sem direito ao evento;
- `record_date`: data de corte para identificar titulares;
- `payment_date`: data prevista/efetiva de pagamento;
- `effective_date`: data em que split ou grupamento passa a valer.

Dividendos/JCP exigem moeda ISO e valor positivo por ação/cota. Splits/grupamentos exigem `split_ratio_from` e `split_ratio_to` positivos e `effective_date`. Valores monetários, taxas e ratios são `Decimal`/`NUMERIC`; `float` é rejeitado.

## Status controlado

- `PENDING`: recebido e aguardando confirmação;
- `CONFIRMED`: payload validado e confirmado;
- `CORRECTED`: versão anterior preservada, mas substituída por correção;
- `CANCELLED`: evento cancelado sem apagar seu histórico;
- `UNAVAILABLE`: campo essencial ausente ou evidência insuficiente.

Ausência de `ex_date` em dividendo/JCP torna o evento `UNAVAILABLE` sem inferência. Payload incompleto, inválido ou conflitante pode ser enviado à quarentena.

## Idempotência e reconciliação

`external_event_key` é determinística e escopada por provider, dataset, instrumento, tipo, identificador externo e datas relevantes. A mesma carga é no-op; o mesmo identificador externo com conteúdo divergente é conflito e vai para quarentena quando não há motivo de correção.

Correções criam nova versão e ligam `supersedes_event_id`/`corrected_event_id` à versão anterior, que permanece auditável com status `CORRECTED`. Cancelamentos criam versão `CANCELLED` com motivo e preservam o evento original. Não há deleção física ou atualização silenciosa.

Falha de um item não derruba os itens válidos do lote. O payload bruto retido é sanitizado e não pode conter tokens, chaves, senhas ou Authorization.

## Licenciamento e DemoProvider

O gateway mantém default deny por provider, plano, endpoint, dataset, finalidade e modalidade. `UNREVIEWED`, acesso interno, feature flag e `DEMO` não concedem licença. O `DemoProvider` fornece somente fixtures sintéticas marcadas `DataLevel=DEMO` e `Freshness=STALE`; nenhuma resposta real é consultada ou aprovada.

## Limite com carteiras

Ingerir um evento corporativo não o aplica a `portfolio_events`. O ledger de usuário permanece append-only e intocado neste dia. O consumo futuro será feito pelo domínio de carteira/performance, com autorização e metodologia explícitas.

Uma projeção de split pode ajustar quantidade pela razão `to/from` e manter o valor econômico equivalente (`quantidade × preço`), sem registrar lucro ou prejuízo artificial. Dividendos/JCP só poderão afetar caixa, custo, P&L ou TWR em etapa posterior, com provider/dataset aprovado e regras documentadas.

## Uso posterior

Os eventos normalizados serão insumo para posições, proventos, P&L, TWR e séries ajustadas. Cada cálculo deverá manter fonte, timestamps, `DataLevel`, `Freshness`, moeda, metodologia e limitações visíveis, conforme a política de integridade financeira.
