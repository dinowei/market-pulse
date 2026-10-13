# ADR-015: Tokens de cor em OKLCH e revisão de contraste dos temas escuro e claro

- Status: Accepted
- Data: 2026-10-07
- Decisores: responsável técnico (Claude Code), com autorização explícita do operador para
  os Dias 33 e 34 da Fase 2. A direção visual (Cláudio) e a aprovação humana do resultado
  visual continuam necessárias, mas nenhuma cor visível mudou, exceto a borda dos campos de
  formulário.
- Relação: diretriz Particle Atlas §8 (identidade cromática), §20 (WCAG 2.2 AA) e ADR-006.

## Contexto

Os tokens `--pa-*` estavam em hex. O roadmap pediu OKLCH, espaço perceptual uniforme, para
derivar tons e temas de forma previsível (Dia 33), e a revisão do tema claro, que já
existia desde o Dia 16, com contraste AA nos dois temas (Dia 34).

## Decisão

1. **OKLCH como fonte da verdade, com fallback hex idêntico.** Os valores OKLCH ficam num
   bloco `@supports (color: oklch(0% 0 0))`, e os hex continuam como base. O suporte a
   `oklch()` é "Baseline Widely available" desde maio de 2023, segundo a MDN. Os valores
   foram gerados da conversão exata sRGB→OKLab (Björn Ottosson) com precisão suficiente
   para voltar ao mesmo hex. Por isso **nenhuma cor existente mudou**; o build confirmou
   que o Lightning CSS do Tailwind preserva `oklch()` e `@supports`.
2. **Novo token `--pa-border-control`**, derivado em OKLCH: mesmo matiz e croma da borda
   `hairline`, com a luminosidade elevada (tema escuro) ou reduzida (tema claro) até
   atingir no mínimo 3,1:1 contra os três fundos (WCAG 2.2, 1.4.11). Os campos de
   formulário (login, busca, watchlists, carteiras e editorial) passam a usá-lo. O
   `hairline` (1,3–1,7:1) fica só para grades e divisórias decorativas.
3. **Revisão do tema claro, medida:** todos os tokens de texto (primário, secundário,
   alta, queda, neutro, stale, indisponível, demo) passam de 4,5:1 sobre canvas, superfície
   e elevado nos dois temas; o par mais apertado é o verde de alta claro sobre o elevado,
   com 4,60:1. O foco passa de 3:1 em todos os fundos. As famílias de matiz são as mesmas
   nos dois temas (verde, vermelho, azul e âmbar, com deriva ≤ 8°).
4. **Correção de semântica:** o aviso de downsampling do Dia 31 usava `.state-note`
   (âmbar); passa a texto neutro, porque o âmbar é reservado a `STALE` e alertas (§8).

## Achados registrados para decisão de design (não alterados)

- **Tema não é global nem persistente.** O botão de tema existe só no dashboard; Watchlists,
  Carteiras e Admin fixam `data-theme="dark"`, a escolha se perde na navegação e o tema não
  segue `prefers-color-scheme`. Torná-lo global exige decidir persistência (armazenamento
  local de preferência, sem sessão ou PII) e evitar o "flash" de tema; cabe à direção visual
  e ao responsável humano.
- **Âmbar como importância de evento.** `.importance-medium` (calendário, Dia 26) usa
  `--pa-state-stale` para importância média, o que desvia da regra "âmbar só para `STALE` ou
  alerta restrito". Precisa de outra codificação (por exemplo, intensidade de cinza ou
  padrão) definida pela direção visual.
- **Paleta alternativa para daltonismo:** continua no Dia 36, com a ressalva já registrada
  no roadmap.

## Evidência

`apps/web/src/lib/color.ts` (conversão e contraste) e `apps/web/app/oklch-tokens-day33.test.ts`:
paridade OKLCH↔hex de todos os tokens, matriz de contraste completa nos dois temas, foco e
borda de controle ≥ 3:1, famílias de matiz e uso do token de controle nos campos. Os testes
de contraste do Dia 28 continuam verdes.
