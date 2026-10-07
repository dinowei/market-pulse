# ADR-018: Visão consolidada da carteira e downsampling alinhado da comparação

- Status: Accepted
- Data: 2026-10-07
- Decisores: responsável técnico (Claude Code), com autorização do operador para executar
  o Dia 35 da Fase 2; o adiamento do downsampling multissérie para o Dia 35 foi decisão do
  usuário ([ADR-016](016-global-persisted-theme.md))
- Relação: resolve H-21 do [handoff](../DAY29_HANDOFF.md); estende a
  [ADR-013](013-history-display-downsampling.md) sem alterá-la; respeita a
  [ADR-007](007-informational-portfolios-ledger-performance.md)

## Contexto

- `/portfolios` fazia 1 lista e mais 8 requisições de detalhe por carteira, e cada
  mutação de watchlist recarregava todas as listas. O fluxo principal do E2E usava 26 das
  30 requisições do balde `standard`.
- A ADR-013 reduz uma série por vez. Na comparação, reduzir cada série sozinha deixaria
  datas diferentes em cada linha e quebraria a leitura ponto a ponto em `INDEX_100`.

## Decisão

1. **`GET /api/v1/portfolios/{id}/overview`** devolve, numa resposta, os mesmos oito
   blocos dos endpoints separados: resumo, eventos, valuation, performance, curva de
   patrimônio, decomposição, proventos e marcadores. A rota chama as mesmas funções das
   rotas separadas, então não há segundo cálculo nem regra nova. Os endpoints separados
   continuam no contrato.
2. **Mesma proteção:** a rota exige sessão e aplica o isolamento por dono das rotas
   separadas (carteira de outro usuário responde 404).
3. **Watchlists:** cada mutação atualiza o estado local com a resposta do servidor
   (`apps/web/src/lib/watchlist-state.ts`), sem recarregar todas as listas.
4. **Downsampling alinhado, opt-in:** `POST /api/v1/market-data/history/batch` aceita
   `max_points` (64–5.000, os mesmos limites da ADR-013). Cada série longa escolhe seus
   pontos M4; todas mantêm a união desses instantes, mais os pontos estruturais (gaps e
   pontos sem valor). Assim, as linhas ficam nas mesmas datas, e cada série conserva seu
   primeiro, último, mínimos, máximos e gaps. A saída continua sendo subconjunto exato dos
   pontos originais, e cada série declara `downsampling` com o total original e o
   devolvido. Sem `max_points`, nada muda.
5. **O limite de 30 requisições por 60 s não foi relaxado.**

## Consequências

- Por leitura de código, a carga de `/portfolios` cai de 9 para 2 requisições (lista e
  overview), e a mutação de watchlist cai de 2 para 1. **Não foi medido em execução**; a
  medição fica para a rodada de frontend.
- Com muitas séries, a união de instantes pode passar de `max_points` por série. O teste
  limita duas séries a no máximo `2 × max_points`.
- O frontend da comparação informa a redução em texto, junto ao gráfico.

## Evidência

- `apps/api/tests/test_portfolio_overview_day35.py`: cada bloco do overview é igual ao
  endpoint separado (exceto `as_of`, o instante do cálculo); isolamento e sessão.
- `apps/api/tests/test_comparison_downsampling_day35.py`: mesmas datas em todas as
  séries, pico de uma e queda da outra preservados, ponto-base do `INDEX_100` mantido,
  série curta intacta, limites do contrato e endpoint em lote.
- `apps/web/app/day35-frontend.test.ts`: `/portfolios` usa `/overview`, e as mutações de
  watchlist não recarregam todas as listas.
