# ADR-006 — Sistema visual monocromático e semântica financeira dos gráficos

- **Status:** Accepted
- **Data:** 2026-08-31
- **Decisores:** responsável do produto, Cláudio e responsável técnico

## Contexto

A direção visual anterior permitia dourado como identidade e não formalizava suficientemente séries únicas, comparações e preservação de preços reais. Isso poderia produzir excesso cromático, linhas decorativas confundidas com dados e comparações distorcidas.

## Decisão

- Preto, branco e cinzas são a identidade predominante.
- Dourado, amarelo e âmbar não são identidade, foco ou seleção; âmbar/laranja fica restrito a status operacional como `STALE`.
- Verde representa `UP`, vermelho `DOWN` e azul `FLAT`/referência, sempre com sinal, texto, ícone ou padrão.
- Uma série real produz exatamente uma linha principal.
- Duas ou mais séries reais produzem múltiplas linhas reais e usam `INDEX_100` por padrão.
- `actual_value`, moeda, unidade, variações, fonte e timestamps permanecem acessíveis junto de `normalized_value`.
- Preço bruto multissérie exige compatibilidade de moeda, unidade, calendário e metodologia, ou FX aprovado.
- Arte Particle Atlas fica separada da camada de verdade e pode ser desligada.

## Consequências

OpenAPI/view models precisarão sustentar valor real e normalizado simultaneamente. Testes matemáticos, visuais, de acessibilidade, gaps e fixtures tornam-se gates. Esta ADR sucede somente orientações cromáticas anteriores incompatíveis, preservando seu histórico; não pressupõe uma ADR-006 anterior.

## Alternativas consideradas

1. Manter dourado como destaque — rejeitado por contrariar a identidade aprovada.
2. Comparar sempre preços brutos — rejeitado por distorcer escalas/moedas.
3. Mostrar somente percentual/índice — rejeitado por esconder valor real.

## Revisão

Revisar com evidência de usabilidade, acessibilidade, performance ou mudança de contrato.
