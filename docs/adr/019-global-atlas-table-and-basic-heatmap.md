# ADR-019: Global Atlas tabular e heatmap básico (P0)

- Status: Accepted
- Data: 2026-10-07
- Decisores: responsável humano pelo produto (prioridade P0 e Dia 37, decididos em
  2026-10-05); implementação por Claude Code, com autorização para executar a Fase 2
  até o Dia 40
- Relação: cumpre a [especificação](../PROJECT_SPEC.md) (escopo P0, itens 3 e 9), a
  [diretriz Particle Atlas](../design/PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md) (§24) e o Dia
  37 do [roadmap](../ROADMAP_30_DAYS.md)

## Conflito de prioridade resolvido pela hierarquia

A [semântica de gráficos](../design/PARTICLE_ATLAS_CHART_SEMANTICS.md) diz que heatmap,
treemap e Global Atlas são "P1/futuros". A especificação, a diretriz (§24), a
arquitetura e o roadmap dizem que o **heatmap básico** e o **Global Atlas em tabela** são
P0. Pela hierarquia do `AGENTS.md`, a especificação prevalece, e o usuário decidiu
entregá-los no Dia 37. Recursos avançados de heatmap e a malha ou o globo do Global Atlas
continuam P1. O texto histórico da semântica de gráficos não foi reescrito; um adendo
datado aponta para esta ADR.

## Dados disponíveis (verificados no código)

- O catálogo (`MASTER_CATALOG` e o catálogo DEMO) tem região, país, bolsa, fuso e moeda,
  mas **não tem setor nem valor de mercado**.
- Nenhum dataset é `PUBLIC_APPROVED`. A variação contra o fechamento anterior só existe no
  modo DEMO, a partir das barras sintéticas.

## Decisão

1. **Global Atlas tabular:** `GET /api/v1/instruments`, que era um stub vazio, passa a
   listar o catálogo com paginação e ordenação (`created_at` mantém a ordem do catálogo,
   que não tem data de criação). `InstrumentSummary` ganha, de forma aditiva, `exchange`,
   `country`, `region` e `timezone`. A página `/atlas` agrupa por região, mostra cobertura
   e estado do dado e **nunca mostra preço**.
2. **Heatmap básico:** `GET /api/v1/market-data/heatmap`. Cada bloco é o mesmo
   `PublicQuote` da rota de cotação, com proveniência própria; nada é recalculado.
3. **O contrato declara o que falta,** em vez de imitar a especificação com dados
   inventados:
   - `grouping = INSTRUMENT_TYPE` (setor indisponível);
   - `sizing = EQUAL_AREA` (valor de mercado indisponível);
   - `color_basis = DIRECTION_VS_PREVIOUS_CLOSE`.

   As três limitações também vêm em texto e aparecem na página.
4. **Membros:** ações, ETFs, FIIs e BDRs do catálogo, fora os `OUT_OF_SCOPE`. Índices
   são referências (benchmarks) e não entram.
5. **Cor só pela direção** (`UP`, `DOWN`, `FLAT`), com sinal, seta e palavra. A escala
   contínua de intensidade fica como heatmap avançado (P1), porque exige limiares e
   validação de contraste próprios. Sem base, o bloco diz "Variação indisponível"; sem
   dataset, "Indisponível".
6. **Tabela equivalente obrigatória** com preço, variação, estado, fonte, horário oficial
   e limitações de cada bloco.

## Consequências

- Quando houver dataset aprovado com setor e valor de mercado, o contrato muda os
  literais (`SECTOR`, `MARKET_CAP`) por nova ADR, sem mexer na página além do rótulo.
- No modo DEMO, o heatmap faz duas leituras por instrumento (cotação e barras), herdadas
  de `public_quote`. Com o catálogo atual, isso é aceitável; para um universo maior, a
  leitura deve ser em lote.
- `GET /instruments` deixa de ser stub, o que ajuda o H-22 (ids padrão do `/compare` a
  partir do catálogo). O H-22 continua aberto até o `/compare` usar essa lista.

## Evidência

- `apps/api/tests/test_global_atlas_heatmap_day37.py`: catálogo com metadados e sem
  preço, ordenação e paginação; blocos iguais à rota de cotação; limitações declaradas;
  no DEMO, variação contra o fechamento anterior e índices fora.
- `apps/web/app/day37-frontend.test.ts`: contrato gerado, pistas de direção, tabela
  equivalente, método visível e nenhum recálculo de valor.
- `apps/web/e2e/day36-wcag.spec.ts` com `/heatmap` e `/atlas`: 25 de 25 em 2026-10-07
  (axe WCAG 2.2 AA nos dois temas, reflow em 320 px, teclado e movimento reduzido), na
  mesma configuração local do Dia 36 (sem sessão, DEMO desligado).
