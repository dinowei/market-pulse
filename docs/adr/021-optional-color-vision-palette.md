# ADR-021: Paleta opcional para daltonismo

- Status: Accepted
- Data: 2026-10-11
- Decisores: responsável humano pelo produto (pediu a implementação em 2026-10-11, item T7
  da sincronização com o NotebookLM); implementação e medição por Claude Code. **Revisão
  visual de Cláudio pendente.**
- Relação: atende à orientação pós-Dia 30 do NotebookLM, que aprova uma "opção de paleta
  para daltonismo"; respeita a diretriz Particle Atlas (§8) e a
  [ADR-006](006-monochrome-financial-chart-semantics.md); complementa a
  [ADR-016](016-global-persisted-theme.md)

## Contexto

O [relatório do Dia 36](../design/ACCESSIBILITY_DAY_36.md) mediu que a paleta padrão não
separa as direções para todas as visões. No tema claro, alta e queda ficam a ΔEok 0,039 em
deuteranopia. Os sinais não cromáticos (sinal, seta e palavra) cobrem a informação, mas a
cor também ajuda quem a distingue.

A paleta azul e laranja foi descartada no Dia 36: laranja é exclusivo de `STALE`, e o azul
significa `FLAT`.

## Decisão

1. **Opção, desligada por padrão.** O botão "Paleta para daltonismo" grava
   `market-pulse.palette = cvd` no navegador e aplica `<html data-palette="cvd">` antes da
   hidratação, pelo mesmo script do tema. Nenhum dado pessoal é guardado.
2. **Mesmas famílias de cor:** verde para `UP` (matiz 140 a 165), vermelho para `DOWN` (10 a
   30) e azul para `FLAT` (240 a 260). Sem laranja. A separação vem da luminosidade.
3. **Valores escolhidos por busca medida:** a combinação, dentro dessas famílias, que
   maximiza a menor distância OKLab entre as três direções em visão normal, protanopia,
   deuteranopia e tritanopia, exigindo contraste de pelo menos 4,5:1 nos três fundos de
   cada tema.

| Tema | `UP` | `DOWN` | `FLAT` | Menor ΔEok (padrão → opção) |
| --- | --- | --- | --- | --- |
| Escuro | `#bddbb6` | `#c4685a` | `#3f82f0` | 0,081 → 0,227 |
| Claro | `#007d1e` | `#5e3532` | `#173f81` | 0,039 → 0,133 |

## Consequências

- As cores da opção são menos saturadas, e o vermelho do tema claro puxa para marrom.
  Por isso a opção precisa da revisão visual de Cláudio antes de qualquer destaque além do
  botão.
- O vermelho da opção não se confunde com o âmbar de `STALE` (ΔEok ≥ 0,13 em todas as
  visões). No tema claro, sob deuteranopia, o verde de alta fica perto do âmbar (0,026);
  `STALE` continua sempre com rótulo em texto.
- Acromatopsia não é resolvida por cor; os sinais não cromáticos seguem obrigatórios nas
  duas paletas.

## Evidência

`apps/web/app/day41-palette.test.ts`: contraste AA em todos os fundos; separação simulada
pelo menos duas vezes maior que a da paleta padrão; desligada por padrão e aplicada antes da
hidratação quando salva. `apps/web/app/theme-global.test.ts`: uma única gravação no
armazenamento, restrita às chaves de tema e paleta. O gate WCAG passou com o botão novo
(33 de 33, local).
