# Normalização de dados de mercado — Dia 10

## Invariantes OHLC

Cada barra exige `canonical_id`, moeda ISO, timestamp com timezone e valores `Decimal`. Deve valer `low <= open <= high`, `low <= close <= high`, `high >= low` e preços estritamente positivos. Itens inválidos são isolados em quarentena; um item inválido não cancela os demais do lote.

## Séries ajustadas

Uma única tabela `price_bars` usa `adjustment_type`: `UNADJUSTED`, `ADJUSTED_SPLIT_ONLY` ou `ADJUSTED_TOTAL_RETURN`. A chave única inclui instrumento, provider, intervalo, timestamp e tipo de ajuste; portanto séries ajustadas e não ajustadas nunca se misturam. Nenhum ajuste é calculado artificialmente sem evento, licença e metodologia documentados.

## Upsert idempotente

Reprocessar a mesma barra com a mesma proveniência é no-op. Conflito no mesmo identificador composto não sobrescreve silenciosamente: fica em quarentena para revisão. A migration `20260901_0003` adiciona o discriminador, vínculo opcional ao ingestion batch, retenção de payload bruto e tabela de quarentena.

## FX

Taxas mantêm `base_currency` e `quote_currency` em direção explícita (USD→BRL é diferente de BRL→USD), timestamp UTC e `Decimal`. Taxa zero, negativa, NaN ou moeda inválida é rejeitada. A constraint existente deduplica por provider, par e timestamp.

## Quarentena e outliers

Registros suspeitos recebem código, identificação do instrumento quando disponível, provider/dataset, request e ingestion batch, hash do payload e campo rejeitado. A política inicial considera variação superior a 50% no lote como `OUTLIER_EXTREME`; o limite é configurável e não constitui regra de mercado.

## Particle Atlas

No futuro, gráficos devem escolher explicitamente o `adjustment_type`, informar fonte, timestamp, moeda e freshness e evitar misturar séries. A normalização fornece dados determinísticos para comparações `INDEX_100`, mantendo valores reais visíveis conforme a diretriz visual.

Nenhum provider real foi ativado, nenhum dado real foi inserido e OpenAPI/cliente permanecem inalterados.
