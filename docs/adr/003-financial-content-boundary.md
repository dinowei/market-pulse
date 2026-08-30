# ADR-003: Limite de conteúdo financeiro

- Status: Accepted
- Data: 2026-08-30
- Decisores: operador do projeto e responsável técnico

## Contexto

Dados e textos financeiros podem induzir ação ou parecer recomendação. Atribuição, atraso e limitação precisam ser verificáveis.

## Decisão

O produto é informativo. Blocos usam tipos controlados, fonte, timestamp e nível do dado. O fluxo é rascunho, validação automática, revisão humana e publicação versionada append-only.

São proibidos recomendação, imperativo, promessa, certeza indevida, preço-alvo próprio, consenso sem fonte e apresentação de `DELAYED`, `EOD` ou `DEMO` como tempo real.

Disclaimer obrigatório: “Conteúdo informativo. Não constitui recomendação de investimento.”

## Alternativas consideradas

- Texto livre sem classificação: simples, risco editorial alto.
- Validador automático sem humano: escalável, incapaz de substituir julgamento.
- Classificação + validação + humano: maior fricção, melhor rastreabilidade.

## Consequências positivas

- Conteúdo auditável, atribuível e corrigível.
- Limites consistentes entre produto e código.
- Redução de alegações impróprias.

## Consequências negativas e riscos

- Publicação mais lenta.
- Léxico pode gerar falso positivo/negativo.
- Exige treinamento e trilha de auditoria.

## Como revisar esta decisão

Revisar com assessoria jurídica/regulatória e evidência de incidentes, sem remover revisão humana silenciosamente.
