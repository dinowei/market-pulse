# Cache, Freshness e Degradação Segura — Dia 12

Este documento é a referência operacional do cache de dados de mercado do MVP.
Ele descreve mecanismos locais e contratos internos; não habilita provider,
redistribuição de dados ou qualquer licença externa.

## Princípios

- PostgreSQL continua sendo a fonte persistente e autoritativa; Redis é uma
  camada de cache e lock, nunca a fonte da verdade.
- `DataLevel` e `Freshness` são conceitos independentes. `REAL_TIME`,
  `DELAYED`, `EOD` e `DEMO` descrevem o nível declarado do dado. `FRESH`,
  `STALE` e `UNAVAILABLE` descrevem sua validade operacional no instante da
  leitura.
- Nenhum cache pode promover `DELAYED`, `EOD` ou `DEMO` para `REAL_TIME`, nem
  criar um timestamp de atualização que não veio da fonte.
- Cada envelope preserva source, dataset, data level, timestamps, moeda,
  limitações e estado de freshness. Valores monetários permanecem `Decimal`;
  serialização JSON não converte valores financeiros para `float`.

## Chaves e TTL

As chaves são determinísticas e granulares, por exemplo
`market_data:quote:{dataset}:{canonical_id}`,
`market_data:history:{dataset}:{canonical_id}:{timeframe}:{adjustment}` e
`market_data:fx:{dataset}:{base}-{quote}`. Consultas negativas usam hash
irreversível do termo; locks usam uma chave específica do dataset e identidade.
Segredos, tokens e URLs de conexão nunca entram em chaves ou mensagens de erro.

O TTL de frescor é definido por `DataLevel` e tipo de dado no módulo
`app.market_data.freshness`. Após o TTL, o envelope pode permanecer até o fim
da janela curta de stale para permitir stale-if-error. Depois dessa janela o
estado é `UNAVAILABLE`.

## Cache-aside e falhas

Em um miss, a aplicação chama o loader substituível e grava o envelope somente
se a fonte retornar um resultado válido. Em hit, a proveniência é preservada.
Se Redis estiver indisponível, o fluxo tenta a fonte sem interromper uma
resposta que possa ser obtida; falhas da fonte podem servir o último envelope
válido como `STALE`. Sem candidato válido, a resposta é controladamente
`UNAVAILABLE`, sem stack trace ou segredo.

Cache negativo é curto (90 segundos no MVP) e distingue `NOT_FOUND`,
`OUT_OF_SCOPE`, `DATA_UNAVAILABLE` e `LICENSE_BLOCKED`. Bloqueio de licença
nunca é mascarado como ausência do instrumento.

## Locks e invalidação

Locks distribuídos têm TTL, owner aleatório e liberação condicionada ao mesmo
owner. A invalidação remove apenas as chaves relacionadas conhecidas; não usa
`FLUSHALL` nem apaga dados de outros datasets.

## Consumo pelo produto

API e frontend devem exibir fonte, horário de atualização, `DataLevel` e
`Freshness`. O Particle Atlas usa esses metadados para diferenciar linha real,
linha stale e indisponibilidade; não deve inferir precisão ou recomendação
financeira a partir da aparência do gráfico.

Esta diretriz não altera rotas públicas nem o contrato OpenAPI no Dia 12.
