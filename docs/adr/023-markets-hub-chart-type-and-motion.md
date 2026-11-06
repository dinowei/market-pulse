# ADR-023: Hub de mercados, tipo de gráfico e camada de movimento do Particle Atlas

- Status: Accepted
- Data: 2026-10-11
- Decisores: responsável humano pelo produto (pediu em 2026-10-11 abas por família de
  mercado, troca do tipo de gráfico e movimento do Particle Atlas "sem pesar e sem
  desconectar do backend"); implementação por Claude Code
- Relação: [ADR-005](005-hybrid-progressive-rendering.md),
  [ADR-006](006-monochrome-financial-chart-semantics.md),
  [ADR-014](014-svg-p0-chart-engine.md), [ADR-019](019-global-atlas-table-and-basic-heatmap.md)
  e [ADR-022](022-day-41-frontend-integration.md)

## Contexto

O usuário listou VALE3, PETR4, CMIN, AAPL, Tesouro Direto (LFT, LTN, NTN-B), CDB, LCI, CRA,
debêntures, IBOV, IFIX, S&P 500, NASDAQ, CDI, IPCA e USD/BRL, e perguntou se existe uma aba
que separe cada família. Pediu ainda a troca do tipo de gráfico e movimento nos visuais,
usando a página de mercados do TradingView como referência.

O que existia antes desta decisão:

- o filtro por classe do Atlas e do heatmap (ADR-022);
- a comparação de até 10 séries;
- só gráfico de linha;
- nenhuma animação.

Conferido no código:

- `MASTER_CATALOG` tinha 5 entradas, e não as 727 linhas que o
  [catálogo documentado](../instruments/MASTER_INSTRUMENT_CATALOG.md) descreve;
- os benchmarks sintéticos devolviam `change_percent` igual a `0.00`, um FLAT inventado;
- a série sintética (fora do DEMO local) já traz OHLC e volume.

A diretriz §6 permite usar terminais como referência de padrões (abas, tabelas, cabeçalho,
período) e proíbe copiar composição, textos, ícones ou sequência de telas. A §18 limita o
movimento a transições (troca de ativo, período, refresh e navegação), com
`prefers-reduced-motion` e sem decoração permanente.

## Decisões

1. **`/markets`, uma aba por família.** As abas são: Visão geral, Ações Brasil, Ações
   internacionais, Índices, Juros e inflação, Câmbio, FIIs, ETFs e BDRs, Cripto, Tesouro
   Direto, Crédito privado e Fundos. A aba Outros só aparece se o catálogo tiver um tipo
   sem família.
   - **Fontes:** as linhas vêm só de `/instruments`, do lote de cotações (em blocos de 10,
     o limite do contrato) e de `/market-data/benchmarks`. A classe vem de
     `instrument_type` e `country`; o benchmark, do `canonical_id` (IPCA vai para Juros e
     inflação).
   - **Página estática:** a aba fica na URL (`?tab=`), lida no cliente dentro de um
     `Suspense`, como na ADR-022.
   - **Abas sem dados:** Tesouro Direto (LFT, LTN, NTN-B), Crédito privado (CDB, LCI, CRA,
     debêntures) e Fundos nomeiam os títulos e dão o motivo da indisponibilidade, sem
     nenhum número.
   - **Acessibilidade:** as abas seguem o padrão WAI-ARIA (setas, Home, End,
     `aria-selected`, painel rotulado).
2. **Seleção entre famílias para comparar.** Marcar séries de qualquer aba leva a
   `/compare?ids=` em INDEX_100, com no máximo 10. Ação contra CDI ou IPCA é possível;
   contra títulos de renda fixa, não, porque não existe série.
3. **VALE3 e CMIN3 entram no catálogo só com metadados** (`CANDIDATE`, `FUTURE_REVIEW`,
   `METADATA_ONLY`). A cotação e o histórico seguem `UNAVAILABLE` com
   `DATASET_NOT_APPROVED`. CMIN3 (CSN Mineração ON) não estava nos exemplos do catálogo
   documentado e foi incluída a pedido do usuário. Nenhum outro instrumento foi importado.
4. **Benchmark sem variação inventada.** `change_percent` passa a ser `null`, porque o nível
   sintético não tem valor anterior oficial. O schema do OpenAPI não muda.
5. **Linha ou candles.**
   - **Quando há candles:** só no modo PRICE e quando toda barra válida traz abertura,
     máxima, mínima e fechamento. Caso contrário, o botão fica desabilitado e o motivo
     aparece em texto.
   - **Pista sem cor:** corpo vazado = alta, cheio = queda, traço = estável. O volume só
     aparece quando todas as barras o trazem, numa faixa com escala própria.
   - **Tabela equivalente:** ganha abertura, máxima, mínima e volume.
   - **Geometria:** fica em funções puras (`chart-geometry.ts`), testadas, ainda em SVG
     (ADR-014).
6. **Camada de movimento (P1, desligável):** `NEXT_PUBLIC_ATLAS_MOTION=off` a remove no
   build.
   - **Gráfico:** a linha se desenha (`stroke-dashoffset`) e os candles e o volume sobem
     em sequência.
   - **Pulso do mercado:** uma partícula por série, agrupada por família, com forma e cor
     da direção. As partículas partem do centro da família quando os dados chegam, quando
     a aba muda ou quando o usuário pede "Atualizar dados", e então param.
   - **Regras:** tamanho igual para todas, nenhuma linha ligando partículas e nada medindo
     preço. O SVG é `aria-hidden`, e a legenda diz as mesmas contagens em texto.
   - **Botão "Arte do pulso":** desliga a arte sem perda de informação.
   - **Movimento reduzido:** com `prefers-reduced-motion`, nenhuma animação roda.

## Diferenças em relação à referência (registradas, não copiadas)

A página de referência tem listas que dependem de dados que não temos aprovados:

- maiores altas e quedas;
- maior volume;
- mais voláteis;
- maiores empresas por valor de mercado;
- calendário de resultados e IPOs;
- índices internacionais além dos benchmarks.

Nenhuma delas foi imitada com dado sintético. Elas entram quando um provider passar no
gate de licença (matriz de licenças).

## Consequências

- **Bundle:** `/markets` mede 189,1 KB gzip, dentro do orçamento de 200 KB.
- **Estado das rotas:** todas as rotas seguem estáticas.
- **Pulso em cinza:** sem DEMO local e sem provider aprovado, toda série fica "sem
  variação conhecida" e o pulso mostra só anéis neutros. É o estado verdadeiro, não falha.
- **Unidade dos benchmarks:** o contrato de benchmark não declara unidade (taxa ao ano ou
  número-índice). A aba Juros e inflação avisa que nenhuma unidade é presumida. Registrado
  como pendência no handoff.
