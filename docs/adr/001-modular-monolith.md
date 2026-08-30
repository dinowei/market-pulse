# ADR-001: Monólito modular

- Status: Accepted
- Data: 2026-08-30
- Decisores: operador do projeto e responsável técnico

## Contexto

O beta reúne identidade, watchlist, mercado, conteúdo e observabilidade, mas tem uma pessoa e 30 dias. Distribuição antecipada aumenta contratos, deploys e diagnóstico.

## Decisão

Adotar monorepo com frontend separado e backend FastAPI como monólito modular. Módulos de domínio não dependem de payload nativo, framework web ou cache como fonte única.

## Alternativas consideradas

- Microserviços: isolamento maior, custo operacional alto.
- Serverless fragmentado: escala por função, contratos e limites dispersos.
- Monólito sem módulos: rápido no início, alto acoplamento.

## Consequências positivas

- Um backend e uma base de migrações.
- Testes e deploy mais simples.
- Extração futura guiada por evidência.

## Consequências negativas e riscos

- Disciplina de fronteiras é obrigatória.
- Falha do backend afeta múltiplos módulos.
- Crescimento sem revisão pode gerar acoplamento.

## Como revisar esta decisão

Revisar quando escala, ownership, segurança ou deploy independente produzirem evidência mensurável de necessidade.
