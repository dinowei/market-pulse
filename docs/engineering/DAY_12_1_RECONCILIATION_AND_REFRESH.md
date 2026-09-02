# Dia 12.1 — reconciliação estrutural e refresh interno

Este documento registra a conclusão do Dia 12.1 e a reconciliação entre o
roadmap e o estado real do código. O trabalho foi limitado a documentação,
guardrails de domínio, uma migration incremental e um orquestrador interno;
nenhum provider real, dado real ou rota pública foi ativado.

## Decisões reconciliadas

- Dias 8 a 11.1 agora refletem catálogo, adapters, normalização, integridade,
  eventos corporativos e reconciliação já executados.
- O refresh idempotente foi realocado para o Dia 12.1, sem apagar o histórico
  do Dia 11. A API pública de catálogo/quotes permanece como objetivo do Dia 13.
- `THIRD_PARTY_CONSENSUS` é o nome canônico de contrato. A enumeração histórica
  `CONSENSUS` permanece no banco para compatibilidade e não é emitida pelo domínio.
- A identidade de instrumento usa `canonical_id`; quotes, barras e FX carregam
  dimensões de dataset, fonte, nível, freshness e ingestão.

## Guardrails implementados

O acesso a datasets pode exigir provider, plano, endpoint, dataset, finalidade,
modalidade, ambiente, evidência e status de licença. A decisão é default deny.
O cache não serve envelopes reais sem `PUBLIC_APPROVED` e evidência; dados DEMO
são explicitamente sintéticos. Adapters candidatos retornam resultados
normalizados, mantendo payload externo dentro da fronteira do adapter.

O refresh é um serviço interno, idempotente por identidade estável, protegido
por lock distribuído e com invalidação granular. Ele não é uma autorização para
ativar provider ou publicar dados.

## Lacunas remanescentes

- A rota pública de catálogo, busca, quotes, histórico, variação e eventos é
  escopo do Dia 13.
- Persistem limitações de cobertura/licença até existir revisão documental
  específica por provider; nenhum dataset é `PUBLIC_APPROVED` por estar no
  catálogo.
- O calendário de freshness local ainda não modela feriados de bolsas.
