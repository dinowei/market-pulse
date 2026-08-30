# ADR-004: Matriz de licenciamento de providers

- Status: Accepted
- Data: 2026-08-30
- Decisores: operador do projeto e responsável técnico

## Contexto

Gratuidade, acesso técnico e licença para redistribuição pública são conceitos diferentes. O beta prioriza fontes gratuitas/delayed, mas não presume permissão.

## Decisão

Cada provider/dataset recebe classe explícita:

```python
class ProviderLicense(str, Enum):
    PUBLIC_COMMERCIAL = 'public_commercial'
    PERSONAL_ONLY = 'personal_only'
    DEMO_LIMITED = 'demo_limited'
    INTERNAL_FALLBACK_ONLY = 'internal_fallback_only'
```

Somente `PUBLIC_COMMERCIAL` pode alimentar resposta pública para usuário comum. Demais classes são bloqueadas por regra de domínio; podem existir para desenvolvimento/teste/fallback interno conforme termos. Estado desconhecido é tratado como não autorizado.

Nenhuma classe definitiva abaixo foi inferida de “gratuito”. A validação exige URL oficial, data de consulta e registro de atribuição/redistribuição.

## Matriz inicial

| Provider/dataset | Classe de licença | Uso permitido agora | Exposição pública | Atribuição | Status |
| --- | --- | --- | --- | --- | --- |
| BCB SGS | A confirmar | Desenvolvimento somente | Bloqueada | A confirmar | Pendente |
| Frankfurter | A confirmar | Desenvolvimento somente | Bloqueada | A confirmar | Pendente |
| Nager.Date | A confirmar | Avaliação de calendário, não cotação | Bloqueada | A confirmar | Pendente |
| brapi | A confirmar | Fixtures/avaliação sem redistribuição | Bloqueada | A confirmar | Pendente |
| Alpha Vantage | A confirmar | Fixtures/avaliação sem redistribuição | Bloqueada | A confirmar | Pendente |
| Twelve Data | A confirmar | Fixtures/avaliação sem redistribuição | Bloqueada | A confirmar | Pendente |
| yfinance | `INTERNAL_FALLBACK_ONLY` conservador | Desenvolvimento/fallback interno | Bloqueada | A confirmar | Pendente de validação |
| Fixtures sintéticas | `DEMO_LIMITED` | Desenvolvimento, teste e demo rotulada | Permitida só como `DEMO` visível | “Dados de demonstração” | Confirmado por decisão interna |

Antes de liberar: verificar termos oficiais, plano, redistribuição, uso comercial, caching, retenção, atribuição, cobertura, delay, quotas e data da revisão.

## Alternativas consideradas

- Lembrete manual: insuficiente e não testável.
- Allowlist por configuração apenas: útil, mas contornável sem regra de domínio.
- Classe persistida + policy de domínio: decisão adotada.

## Consequências positivas

- Default deny para exposição pública.
- Auditoria e testes explícitos.
- Troca de provider sem alterar domínio.

## Consequências negativas e riscos

- Beta pode iniciar somente com `DEMO`.
- Termos mudam e exigem revisão periódica.
- Dataset pode ter regra diferente do provider.

## Como revisar esta decisão

Revisar por dataset após consulta documental oficial e sempre que termos, plano ou público mudarem.
