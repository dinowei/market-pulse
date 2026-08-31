# ADR-005 — Estratégia de renderização híbrida e progressiva

- **Status:** Accepted
- **Data:** 2026-08-31
- **Decisores:** responsável do produto e responsável técnico

## Contexto

Particle Atlas precisa expressar densidade e movimento sem sacrificar acessibilidade, desempenho ou verdade financeira. Canvas/WebGL prematuros podem bloquear o P0 e criar fallback incompleto.

## Decisão

- HTML/CSS são o padrão para estrutura e UI acessível.
- SVG atende eixos, labels, ícones e séries moderadas.
- Canvas 2D só entra com justificativa medida de densidade/performance e equivalente acessível.
- WebGL/Three.js é P1, lazy-loaded, feature-flagged, com fallback e nunca integra o bundle P0 comum.
- Arte visual fica separada da camada de verdade, apresentação e acessibilidade.
- Movimento respeita `prefers-reduced-motion`, pausa fora da viewport/aba oculta e degrada antes de afetar dados.

## Consequências

O beta mantém uma experiência funcional sem efeitos avançados. Cada adoção de biblioteca exige análise de licença, manutenção, bundle, a11y e desempenho; a ausência de WebGL não reduz informação.

## Alternativas consideradas

- WebGL obrigatório: rejeitado por custo, acessibilidade e risco de bloqueio.
- Canvas para toda a UI: rejeitado por pior semântica e teclado.
- Renderização decorativa sem medição: rejeitada por não ser auditável.

## Revisão

Revisar após medições reais de densidade, frame time, bundle e dispositivos; mudança material exige nova decisão.
