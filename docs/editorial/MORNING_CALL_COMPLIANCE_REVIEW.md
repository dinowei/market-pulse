# Pacote de revisão de compliance do Morning Call (H-13)

- **Data:** 2026-10-07 (UTC), Dia 35.
- **Estado:** **aguardando revisão humana.** Este documento prepara a revisão; ele não
  é a revisão nem a aprovação.
- **Escopo:** Morning Call e avisos das áreas financeiras do frontend, comparados com a
  [política de conteúdo financeiro](../policies/FINANCIAL_CONTENT_POLICY.md).
- **Uso permitido até a assinatura:** somente uso pessoal no staging privado. Qualquer
  outro uso exige a assinatura da seção 5 (critério de pronto de H-13 no
  [handoff](../DAY29_HANDOFF.md)).

## 1. O que foi corrigido no Dia 35

| Ponto | Antes | Depois | Prova |
| --- | --- | --- | --- |
| Aviso editorial do Morning Call (§11) | Texto próprio ("orientação de investimento, oferta ou solicitação de ordem") | Texto canônico completo do §11 | `apps/web/app/compliance-day35.test.ts` compara o texto com a política |
| Aviso mínimo nas áreas financeiras (§11) | "Dados informativos; não constituem recomendação financeira." só no dashboard e na watchlist | Texto canônico em dashboard, watchlists, carteiras, calendário e comparação | Mesmo teste, um caso por componente |
| Origem do texto | Copiado à mão em cada componente | Constantes únicas em `apps/web/src/lib/disclaimers.ts` | O teste falha se a política mudar e o código não |
| Acentuação do painel | "conteudo", "Indisponivel", "versao", "Historico" | Grafia correta | Mesmo teste |
| Texto oculto só para teste | `<span class="sr-only" aria-hidden>` com palavras exigidas pelo teste antigo | Removido; os estados reais têm a grafia exigida | Mesmo teste |

## 2. Cobertura do validador automático

Fonte: `apps/api/app/editorial/validator.py`. O validador roda na transição para
`PUBLISHED` e bloqueia a publicação se houver violação
(`apps/api/app/editorial/service.py`, `transition_by_id`).

| Regra da política | Código da violação | Cobertura |
| --- | --- | --- |
| §3 "compre", "entre agora", "saia agora", "vai subir/cair", lucro/retorno garantido, sinal de compra/venda | `PRESCRIPTIVE_LANGUAGE` | Coberta por lista de padrões com fronteira de palavra e texto sem acento |
| §3 "venda" | `PRESCRIPTIVE_LANGUAGE` | **Parcial:** só "venda" seguido de ticker ou de "agora" |
| §3 "mantenha" | `PRESCRIPTIVE_LANGUAGE` | Coberta, sem análise de contexto |
| §3 preço-alvo próprio, "compra forte", carteira recomendada | nenhum | **Não coberta:** depende da revisão humana |
| §3 recomendação personalizada, cenário como certeza, terceiro como autoria própria | nenhum | **Não coberta:** exige análise de contexto |
| §2/§6 `FACT` com fonte | `FACT_SOURCE_REQUIRED` | Coberta (presença de fonte) |
| §4 consenso com fonte e atribuição | `CONSENSUS_SOURCE_REQUIRED`, `CONSENSUS_ATTRIBUTION_REQUIRED` | Coberta |
| §4 consenso com data, metodologia e licença | nenhum | **Não coberta:** `retrieved_at` é opcional e não há campo de metodologia nem de licença |
| §5 linguagem condicional e fontes | `SCENARIO_CONDITIONAL_LANGUAGE_REQUIRED`, `SCENARIO_SOURCE_REQUIRED` | Coberta (presença de termo condicional e de fonte) |
| §5 horizonte e fatores de invalidação | nenhum | **Não coberta** |
| `RISK` com fonte | `RISK_SOURCE_REQUIRED` | Coberta |
| §10 ordem das 11 seções do Morning Call | nenhum | **Não coberta** |
| §13 "tempo real" para `DEMO` ou `STALE` | nenhum | **Não coberta** no texto editorial; o frontend mostra `DataLevel` e `Freshness` dos dados |

A política (§3) diz que a validação automática sinaliza, mas não substitui a análise de
contexto. As linhas "não coberta" são o roteiro da revisão humana.

## 3. Divergências entre política e código

| # | Política | Código | Impacto |
| --- | --- | --- | --- |
| D-1 | Fluxo `DRAFT → VALIDATED/VALIDATION_FAILED → IN_REVIEW → PUBLISHED → SUPERSEDED` (§9) | `DRAFT → UNDER_REVIEW → APPROVED → PUBLISHED → ARCHIVED`; a validação só bloqueia na publicação | Um rascunho inválido pode chegar à revisão; ele não chega ao público |
| D-2 | Aprovação humana registra responsável e timestamp (§9) | `editorial_review_events` grava `actor_user_id`, `from_status`, `to_status` e `created_at` | Coberta |
| D-3 | Revisão humana obrigatória (§9) | O papel `ADMIN` pode criar, aprovar e publicar o mesmo post; não há regra de duas pessoas | Uma única pessoa pode publicar sozinha |
| D-4 | Versão anterior auditável (§9) | Trigger `editorial_versions_append_only` (migration 0008) impede alterar versões | Coberta |
| D-5 | Data de arquivamento | Ao arquivar, `archived_at` recebe `published_at` (o instante da publicação), não o instante do arquivamento | O evento em `editorial_review_events` tem o horário correto; o campo do post não |

D-1 e D-3 mudam o fluxo editorial e exigem ADR antes de qualquer correção. D-5 é um
defeito de auditoria de baixo impacto, registrado para o Dia 39 (regressão).

## 4. Roteiro da revisão humana

Para cada Morning Call publicado:

1. Ler cada bloco e confirmar que nenhum texto induz compra, venda, manutenção, timing
   ou alocação, inclusive em linguagem indireta (§3).
2. Confirmar que não há preço-alvo, classificação própria ou carteira sugerida (§3).
3. Para `THIRD_PARTY_CONSENSUS`, conferir fonte, data, metodologia e licença na
   [matriz de licenças](../DATA_PROVIDER_LICENSE_MATRIX.md) (§4 e §8).
4. Para `CONDITIONAL_SCENARIO`, conferir horizonte e fatores de invalidação (§5).
5. Conferir a ordem das seções e a marcação explícita das seções sem evidência (§10).
6. Conferir que dados `DEMO`, `DELAYED`, `EOD` ou `STALE` não aparecem como atuais (§7).
7. Conferir que o aviso editorial completo aparece junto ao conteúdo (§11).

## 5. Assinatura

| Campo | Valor |
| --- | --- |
| Revisor responsável | *pendente* |
| Data e hora (UTC) | *pendente* |
| Decisão | *pendente* (aprovado, aprovado com ressalvas ou reprovado) |
| Ressalvas | *pendente* |

Sem esta assinatura, H-13 continua aberto e o Morning Call não sai do uso pessoal.
