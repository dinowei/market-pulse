# Matriz operacional de licenciamento de providers e datasets

- **Status:** Canônica para revisão operacional; todos os candidatos externos começam bloqueados
- **Data inicial:** 2026-08-30
- **Decisão relacionada:** [ADR-004](adr/004-provider-licensing-matrix.md)
- **Política relacionada:** [Política de Conteúdo Financeiro](policies/FINANCIAL_CONTENT_POLICY.md)

Esta matriz registra evidência; não concede direitos por inferência. A classe conceitual da ADR-004 e o status de revisão abaixo são dimensões diferentes. Para uso público, a combinação exata deve ter status `PUBLIC_APPROVED`, evidência oficial vigente e classe compatível. Qualquer campo ausente ou duvidoso resulta em bloqueio por default deny.

## Status de revisão permitidos

- `UNREVIEWED`: evidência ainda não verificada; bloqueado para uso público e integração real.
- `REJECTED`: evidência avaliada e incompatível com o uso pretendido; bloqueado.
- `DEVELOPMENT_ONLY`: uso real limitado ao desenvolvimento conforme evidência; nunca exposição pública.
- `PUBLIC_APPROVED`: uso público aprovado somente para a combinação e condições registradas.

`DEMO`, autenticação administrativa, feature flag, allowlist, acesso interno ou disponibilidade técnica não mudam o status nem concedem licença.

## Schema obrigatório por registro

| Campo | Regra |
| --- | --- |
| Provider | Entidade contratual/fonte identificada |
| Plano | Plano ou regime de acesso exato |
| Endpoint | Endpoint/recurso exato; não aceitar “API inteira” sem evidência |
| Dataset | Conjunto de dados e cobertura aplicável |
| Finalidade | Desenvolvimento, demonstração pública ou outra finalidade específica |
| Modalidade de uso | Busca, armazenamento, cache, transformação, exibição e/ou redistribuição |
| Status de revisão | Um dos quatro valores permitidos |
| Classe ADR-004 | Classe conceitual aplicável após revisão; vazia enquanto desconhecida |
| Evidência oficial | URL/documento oficial, versão e trecho ou referência verificável |
| Data da revisão | Data UTC da revisão humana |
| Revisor | Identidade responsável pela decisão |
| Atribuição | Texto/local obrigatório ou “não exigida”, somente com evidência |
| Restrições | Quotas, delay, retenção, cache, região, comercialidade e outras condições |
| Próxima revisão | Data/evento que invalida ou reabre a avaliação |

## Candidatos iniciais

Os nomes abaixo vieram da ADR-004 como candidatos históricos. Nenhum plano, endpoint, dataset, permissão, atribuição, quota ou latência foi confirmado nesta tarefa; campos desconhecidos permanecem explicitamente vazios.

| Provider | Plano | Endpoint | Dataset | Finalidade | Modalidade de uso | Status | Classe ADR-004 | Evidência oficial | Revisão/revisor | Atribuição e restrições |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BCB SGS | — | — | — | Avaliação futura | — | `UNREVIEWED` | — | — | — | Bloqueado |
| Frankfurter | — | — | — | Avaliação futura | — | `UNREVIEWED` | — | — | — | Bloqueado |
| Nager.Date | — | — | — | Avaliação futura de calendário | — | `UNREVIEWED` | — | — | — | Bloqueado |
| brapi | — | — | — | Avaliação futura | — | `UNREVIEWED` | — | — | — | Bloqueado |
| Alpha Vantage | — | — | — | Avaliação futura | — | `UNREVIEWED` | — | — | — | Bloqueado |
| Twelve Data | — | — | — | Avaliação futura | — | `UNREVIEWED` | — | — | — | Bloqueado |
| yfinance | — | — | — | Avaliação futura | — | `UNREVIEWED` | — | — | — | Bloqueado |

Fixtures sintéticas internas não são aprovação de provider. Elas podem ser usadas como `DEMO` somente quando determinísticas, rotuladas, sem cópia de dados reais protegidos e sem sugerir mercado atual.

## Processo de revisão

1. Definir uma única combinação de provider, plano, endpoint, dataset, finalidade e modalidade.
2. Consultar termos e documentação oficiais atuais; não usar resumo de terceiros como evidência decisiva.
3. Registrar uso comercial, armazenamento, cache, transformação, exibição, redistribuição, atribuição, região, plano, quotas e delay.
4. Registrar URL/documento, versão/data, revisor e próxima revisão.
5. Classificar como `REJECTED`, `DEVELOPMENT_ONLY` ou `PUBLIC_APPROVED`; dúvida permanece `UNREVIEWED`.
6. Submeter mudança a CODEOWNERS e testar o license gate.
7. Reabrir a revisão quando termos, plano, endpoint, dataset, finalidade, modalidade ou público mudarem.

## Gate técnico futuro

A configuração efetiva deve referenciar um registro estável desta matriz. Ausência, divergência de dimensões ou status diferente de `PUBLIC_APPROVED` deve impedir exposição pública. Nenhum fallback pode contornar o gate: snapshot antigo de fonte não aprovada continua bloqueado.
