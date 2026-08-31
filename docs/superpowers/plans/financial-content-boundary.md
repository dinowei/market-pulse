# Plano técnico canônico da fronteira de conteúdo financeiro

- **Status:** Planejado; nenhuma implementação autorizada no Dia 1
- **Data:** 2026-08-30
- **Política normativa:** [FINANCIAL_CONTENT_POLICY.md](../../policies/FINANCIAL_CONTENT_POLICY.md)

Este plano traduz a política financeira em controles técnicos futuros. Em conflito, a política canônica prevalece. Exemplos são simbólicos e não representam dados de mercado.

## Objetivos e invariantes

- aceitar exatamente `FACT`, `THIRD_PARTY_CONSENSUS`, `CONDITIONAL_SCENARIO`, `RISK` e `LIMITATION`;
- separar `DataLevel` (`REAL_TIME`, `DELAYED`, `EOD`, `DEMO`) de `Freshness` (`FRESH`, `STALE`, `UNAVAILABLE`);
- impedir recomendação, sinal, promessa, preço-alvo próprio ou orientação personalizada;
- exigir proveniência, licença aplicável, timestamps, limitações, validação e revisão humana;
- manter publicações versionadas e append-only;
- falhar fechado: ausência de evidência mantém rascunho não publicável ou dado `UNAVAILABLE`.

## Modelo conceitual futuro

### FinancialContent

- `id`: identificador estável do conteúdo lógico;
- `version`: inteiro crescente;
- `content_type`: enum exato da política;
- `status`: `DRAFT`, `VALIDATION_FAILED`, `VALIDATED`, `IN_REVIEW`, `PUBLISHED` ou `SUPERSEDED`;
- `title` e `body`;
- `created_at`, `created_by`;
- `supersedes_version_id`, quando houver correção;
- `change_reason`, obrigatório em nova versão de conteúdo já publicado;
- `content_hash`, para integridade/auditoria, sem substituir imutabilidade do banco.

### Evidence

- `source_name` e referência oficial;
- provider, plano, endpoint e dataset, quando aplicáveis;
- finalidade e modalidade de uso;
- timestamp da fonte e timestamp da coleta;
- trecho factual/metodologia suficiente para revisão;
- referência à evidência de licença e sua data de revisão;
- limitações e atribuição obrigatória.

### DataClassification

- `data_level` e `freshness` em campos separados;
- atraso conhecido para `DELAYED`;
- motivo, início e último timestamp válido para `STALE`;
- motivo de indisponibilidade para `UNAVAILABLE`.

### ReviewRecord

- resultado da validação automática e regras acionadas;
- revisor humano, decisão e timestamp;
- comentário de revisão;
- versão exata analisada;
- identidade administrativa auditável.

## Pipeline de estados

```text
DRAFT
├─ validação falha ─> VALIDATION_FAILED ─> correção cria/atualiza rascunho
└─ validação passa ─> VALIDATED ─> IN_REVIEW
                                      ├─ rejeição ─> DRAFT/VALIDATION_FAILED
                                      └─ aprovação humana ─> PUBLISHED
PUBLISHED ─> correção em nova versão ─> PUBLISHED (nova) + SUPERSEDED (anterior)
```

Nenhuma automação publica diretamente. O comando administrativo prepara ou submete conteúdo, mas autenticação administrativa e feature flags não substituem revisão, licença nem política.

## Validação futura

A validação deve combinar schema e regras contextuais:

1. verificar `ContentType`, campos mínimos e estado;
2. validar evidências, atribuição, timestamps e classificações;
3. consultar a combinação exata na matriz de licenças;
4. rejeitar conteúdo sem `PUBLIC_APPROVED` quando destinado ao público;
5. sinalizar linguagem prescritiva, promessa e previsão certa com fronteiras de palavra, negações, citações e contexto;
6. aplicar requisitos específicos a consenso, cenário, risco e limitação;
7. registrar resultado determinístico e explicável;
8. exigir revisão humana posterior.

Validação lexical isolada não deve apagar exemplos, citações ou negações legítimas, mas falsos positivos são preferíveis à publicação automática de conteúdo proibido. A decisão humana não pode aprovar o que a política proíbe.

## Morning Call

O comando administrativo futuro deve:

- receber um artefato estruturado, nunca gerar texto por IA;
- criar `DRAFT` e versões, sem `UPDATE`/`DELETE` de publicação;
- exigir as onze seções e regras definidas na política, permitindo omissão explícita por falta de evidência;
- executar validação antes de encaminhar a `IN_REVIEW`;
- registrar autor, revisor, horários e motivo de correção;
- publicar somente após ação humana separada e autorizada;
- exibir disclaimer, fontes e limitações junto ao conteúdo.

Não haverá editor visual, autopublicação, recomendação ou personalização no beta.

## Licenciamento e dados

A fronteira consulta [DATA_PROVIDER_LICENSE_MATRIX.md](../../DATA_PROVIDER_LICENSE_MATRIX.md) por provider, plano, endpoint, dataset, finalidade e modalidade. Estado ausente ou `UNREVIEWED`, `REJECTED` ou `DEVELOPMENT_ONLY` bloqueia uso público. `DEMO`, allowlist, login admin ou ambiente interno não mudam o resultado.

Fixtures devem ser sintéticas, determinísticas, identificadas como demonstração e não derivadas de dados reais protegidos.

## Persistência append-only

- publicação é inserção de versão imutável;
- correção referencia a versão anterior e registra motivo;
- versão substituída continua auditável como `SUPERSEDED`;
- aplicação e banco devem impedir alteração/exclusão silenciosa;
- transação deve gravar versão, revisão e evento de auditoria de forma atômica;
- exportação/auditoria deve reconstruir a cadeia completa.

## API administrativa futura

Rotas e comando exatos serão definidos no dia autorizado. A fronteira deve separar criação, validação, submissão, revisão e publicação; autenticar cada ação; usar Problem Details; não retornar segredos; e aplicar autorização por papel/escopo. Endpoint administrativo não é público e não concede licença.

## Testes essenciais futuros

- cada `ContentType` válido e qualquer valor desconhecido;
- transições permitidas e proibidas;
- publicação sem revisão humana;
- correção append-only e tentativa de mutação/exclusão;
- falta de fonte, timestamp, limitação, atribuição ou licença;
- `DataLevel` e `Freshness` independentes;
- `DEMO`/admin/feature flag incapazes de contornar licença;
- consenso sem metodologia/atribuição;
- cenário sem condição, incerteza ou invalidação;
- linguagem de recomendação, promessa, sinal e preço-alvo próprio;
- negação, citação e exemplo editorial para reduzir falsos positivos;
- concorrência e idempotência de publicação;
- autorização horizontal/vertical e trilha de auditoria;
- disclaimer e metadados visíveis no frontend.

## Sequenciamento e gates

- **Dia 4:** suportes de persistência/migração, sem implementar conteúdo completo.
- **Dia 5:** contratos e erros administrativos genéricos.
- **Dia 20:** implementação autorizada da fronteira, comando, revisão e exibição.
- **Dias 25–27:** E2E, hardening, auditoria, logs e runbook.

O plano não autoriza antecipação. Mudança do fluxo editorial, enums, imutabilidade, regra de licença ou natureza informativa exige revisão da política e, quando material à arquitetura, ADR.

## Critérios de conclusão da fronteira

- política mapeada para schema, domínio, banco, API, comando e UI;
- nenhum caminho publica sem validação e revisão humana;
- licença default deny é testada no domínio;
- versões publicadas não são mutadas nem apagadas silenciosamente;
- conteúdo proibido falha fechado e produz evidência de validação;
- Morning Call mostra fontes, tempos, limitações e disclaimer;
- testes de segurança, autorização, concorrência e auditoria passam.
