# Performance factual de carteiras — Dia 21

## Escopo

O Dia 21 transforma o ledger append-only em uma leitura auditável de valuation,
P&L e performance. Os cálculos são informativos: não constituem recomendação,
suitability, promessa de retorno ou instrução de compra/venda.

## Valuation

O motor reaplica os eventos em ordem determinística usando `Decimal`. Para cada
posição aberta, calcula `quantity × last_approved_price` na moeda nativa e
converte para a moeda-base somente quando existe FX explícito no sentido
`origem -> moeda-base`. Caixa em moeda estrangeira segue a mesma regra.

As marcas disponíveis no P0 são fixtures sintéticas locais (`DataLevel=DEMO`,
`Freshness=STALE`, provider `demo`); elas não representam mercado real. Sem
preço ou FX, a resposta é `PARTIAL`/`UNAVAILABLE`, lista `missing_inputs` e
nunca inventa um valor.

## P&L

P&L realizado deriva de cada venda pelo custo médio ponderado vigente, líquido
de taxa. P&L não realizado é valor de mercado menos custo remanescente. Taxas de
compra entram no custo; taxas de venda reduzem o resultado realizado. Reversões
são novos eventos e compensam o evento original sem mutá-lo.

## TWR

`calculate_twr` compõe multiplicativamente os subperíodos. Cada fluxo externo
(`CASH_DEPOSIT` ou `CASH_WITHDRAWAL`) é removido do valor final do subperíodo;
compras e vendas permanecem movimentações internas. A API retorna TWR como
`UNAVAILABLE` enquanto não houver uma série histórica de valuation aprovada;
isso evita transformar uma marca DEMO atual em histórico fictício.

## Equity curve e decomposição

`equity-curve` expõe pontos nas datas do ledger, com patrimônio, caixa, posições,
`DataLevel`, `Freshness`, estado e dados ausentes. Não há interpolação ou
suavização. A decomposição P0 informa efeito de preço quando disponível e
mantém FX, fluxos, taxas e proventos como indisponíveis sem série histórica
adequada.

## Contrato e endpoints

Todos os endpoints são privados, exigem sessão opaca e aplicam isolamento por
`current_user.id`; carteira de outro usuário responde `404`.

- `GET /api/v1/portfolios/{portfolio_id}/valuation`
- `GET /api/v1/portfolios/{portfolio_id}/performance`
- `GET /api/v1/portfolios/{portfolio_id}/equity-curve`
- `GET /api/v1/portfolios/{portfolio_id}/performance/decomposition`

Cada resposta carrega metodologia, estado, fonte/provider/dataset e timestamps
de proveniência. O frontend usa exclusivamente os tipos OpenAPI gerados e
oferece fallback tabular para a equity curve.

## Fora do Dia 21

Não foram implementados provider real, dados reais, WebSocket, WebGL/Three.js,
Morning Call, corretora, rebalanceamento, otimização ou recomendação financeira.
