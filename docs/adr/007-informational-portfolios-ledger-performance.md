# ADR-007 — Carteiras informativas, ledger de eventos e cálculo factual de performance

- **Status:** Accepted
- **Data:** 2026-08-31
- **Decisores:** responsável do produto e responsável técnico

## Contexto

O beta precisa acompanhar carteiras próprias sem se tornar serviço de gestão ou recomendação. Resultados devem ser reconstruíveis a partir de eventos, snapshots, preços, FX e metodologia explícita.

## Decisão

- O usuário pode criar múltiplas carteiras próprias e registrar manualmente compras, vendas, aportes, retiradas, taxas e proventos.
- O sistema calcula factual e informativamente posições, custo, patrimônio, P&L, rentabilidade, proventos e performance histórica.
- O ledger é versionado/append-only; correções criam novos eventos auditáveis, não mutações silenciosas.
- A base, moeda, timestamps, metodologia, preço, FX e estado de cada cálculo ficam visíveis.
- Dados faltantes produzem `PARTIAL` ou `UNAVAILABLE`, nunca zeros ou inferências silenciosas.
- A funcionalidade não é gestão de carteira, recomendação, suitability, ordem, alocação sugerida, promessa de retorno ou integração com corretora.
- Carteiras e eventos são isolados por usuário e autorizados no backend.

## Consequências

Persistência, contrato e testes precisarão reconstruir posições e resultados. Custo médio, retorno ponderado pelo tempo/dinheiro, proventos, taxas e FX exigem metodologia documentada; não há alegação de conformidade GIPS.

## Alternativas consideradas

- Gestão automatizada: rejeitada por escopo, risco regulatório e ausência de autorização.
- Importação automática de corretora: adiada por licença, segurança e complexidade.
- Edição destrutiva de eventos: rejeitada por perda de auditoria.

## Revisão

Revisar após testes de domínio, segurança, privacidade e metodologia; expansão para automação ou recomendação exige nova aprovação.
