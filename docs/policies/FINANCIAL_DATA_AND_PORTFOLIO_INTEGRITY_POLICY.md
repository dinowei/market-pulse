# Política de integridade de dados financeiros e carteiras

Status: canônica e obrigatória para qualquer dado financeiro exibido ou calculado pelo Market Pulse.

## Princípios

O Market Pulse nunca deve exibir preço, rentabilidade, valuation, gráfico ou carteira sem indicar fonte, horário, nível do dado, atualidade e metodologia aplicável.

Toda exibição de preço, série, P&L, TWR ou carteira deve incluir, no mínimo: fonte, DataLevel, Freshness, timestamp oficial e timestamp de coleta.

Catálogo mestre é metadado estático. Existir no catálogo não significa ter cotação disponível. Provider candidato não é provider aprovado; `PUBLIC_APPROVED` só pode ser concedido por decisão humana e documental.

## Níveis, atualidade e proveniência

- `DataLevel`: `REAL_TIME`, `DELAYED`, `EOD` ou `DEMO`.
- `Freshness`: `FRESH`, `STALE` ou `UNAVAILABLE`.
- Todo dado exige provider, dataset, fonte, timestamp oficial, timestamp de coleta, latência conhecida, moeda e limitações.
- `DEMO` é sintético e claramente rotulado; nunca pode parecer real-time.
- `DELAYED` e `EOD` devem informar a defasagem/metodologia. `STALE` identifica último dado válido, nunca dado atual.
- `UNAVAILABLE` não pode ser convertido em zero, estimativa ou preço inventado.

## Licenciamento e Default Deny

Cada combinação provider/plano/endpoint/dataset/finalidade/modalidade começa bloqueada. Ausência de evidência, `UNREVIEWED`, sandbox, acesso interno, feature flag, autenticação administrativa ou `DEMO` não concedem licença. Dado real só pode alcançar API pública após `PUBLIC_APPROVED` explícito e vigente.

## Catálogo e séries

O identificador primário é `canonical_id`, nunca ticker isolado. O frontend e a API devem expor o nível de suporte do instrumento.

Séries usam `UNADJUSTED`, `ADJUSTED_SPLIT_ONLY` ou `ADJUSTED_TOTAL_RETURN` com rótulo explícito. Séries ajustadas e não ajustadas não podem compartilhar registro sem discriminador. Nenhuma série ajustada é fabricada sem evento corporativo, licença e metodologia documentados.

## OHLC, FX e quarentena

Para cada barra: `low <= open <= high`, `low <= close <= high`, preços positivos, volume exato, moeda ISO e timestamp timezone-aware. Violação, outlier extremo, moeda incompatível, payload incompleto ou ajuste sem rótulo vai para quarentena sem derrubar itens válidos do lote.

FX mantém direção explícita (`USD -> BRL` é diferente de `BRL -> USD`), taxa `Decimal`, timestamp UTC, provider/dataset e deduplicação por par, fonte e instante. Taxas zero, negativas, NaN ou inválidas são rejeitadas.

## Carteiras e cálculos

Carteiras são informativas e baseadas em ledger append-only. Eventos não são atualizados nem apagados; correções usam reversão ou novo evento.

- P&L nominal é diferença factual entre custo, proventos e valor marcado; não é recomendação.
- TWR mede rentabilidade isolando aportes e saques externos e deve declarar período, método e dados faltantes.
- No P0, a marcação usa o último preço aprovado disponível, com `DataLevel` e `Freshness` visíveis. Ausência de preço aprovado mantém posição sem fingir valuation.
- Bid/ask para P&L preciso é P1/pós-beta e depende de provider licenciado; não deve ser inferido de último preço.
- Nenhum cálculo usa `float`; dinheiro, preço, taxa, quantidade e câmbio usam `Decimal` ou tipo exato equivalente.

## Contrato mínimo de exibição

Frontend, relatórios, Morning Call, gráficos Particle Atlas e endpoints públicos devem carregar:

- fonte, provider e dataset;
- `DataLevel` e `Freshness`;
- timestamp oficial e timestamp de coleta;
- moeda;
- metodologia quando houver cálculo;
- aviso para `DEMO`, `EOD`, `DELAYED`, `STALE` ou `UNAVAILABLE`.

O frontend nunca renderiza preço, série, P&L, TWR, rentabilidade ou carteira como plenamente atual quando a API não entrega esse contexto. Particle Atlas representa séries reais, preserva valores reais e oferece fallback tabular acessível.

## Conteúdo e comunicação

Morning Call é factual e não prescritivo. Nenhuma tela, texto ou gráfico pode recomendar compra, venda, manutenção, timing, alocação, suitability ou promessa de retorno. A política financeira não é substituída por disclaimer.
