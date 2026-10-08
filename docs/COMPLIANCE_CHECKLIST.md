# Checklist de compliance: controles e evidências

- **Data:** 2026-10-07 (Dia 40).
- **Natureza:** índice para auditoria. Cada linha liga um controle à norma do repositório
  e à prova (teste, código ou documento). Não substitui as políticas, não é parecer
  jurídico e não declara conformidade com nenhuma regulação.
- **Legenda de estado:** **Implementado** (código e teste); **No staging** (implantado no
  commit `60df9ca`); **Pendente** (falta algo dito na linha); **Lacuna** (nada existe
  ainda).

## 1. Conteúdo financeiro

| Controle | Norma | Prova | Estado |
| --- | --- | --- | --- |
| Produto informativo, sem recomendação, sinal ou preço-alvo | [Política de conteúdo](policies/FINANCIAL_CONTENT_POLICY.md) §1–§3 | Validador editorial `PRESCRIPTIVE_LANGUAGE` (`apps/api/app/editorial/validator.py`) | Implementado; no staging |
| Avisos legais com o texto literal do §11 | Política §11 | `apps/web/src/lib/disclaimers.ts`; `compliance-day35.test.ts` compara com a política | Implementado; **não** no staging |
| Fontes obrigatórias em fato, consenso, cenário e risco | Política §4–§5 | Códigos `FACT_SOURCE_REQUIRED`, `CONSENSUS_*`, `SCENARIO_*` e `RISK_SOURCE_REQUIRED` | Implementado; cobertura parcial mapeada no pacote abaixo |
| Revisão humana do Morning Call | Política §9–§10 | [Pacote de revisão](editorial/MORNING_CALL_COMPLIANCE_REVIEW.md) | **Pendente: assinatura** (H-13) |
| Fluxo editorial igual ao da política | Política §9 | Divergências D-1 e D-3 no pacote; D-5 corrigida no Dia 39 | **Pendente: ADR** (H-25) |

## 2. Dados de mercado e licenciamento

| Controle | Norma | Prova | Estado |
| --- | --- | --- | --- |
| `default deny` por provider, plano, endpoint, dataset e finalidade | [ADR-004](adr/004-provider-licensing-matrix.md); [matriz](DATA_PROVIDER_LICENSE_MATRIX.md) | 11 providers distintos, todos `UNREVIEWED`; nenhum `PUBLIC_APPROVED` | Implementado; só dados `DEMO` sintéticos |
| Fonte, horários, `DataLevel`, `Freshness` e limitações em todo dado exibido | [Política de integridade](policies/FINANCIAL_DATA_AND_PORTFOLIO_INTEGRITY_POLICY.md) | Validador de proveniência em `PublicQuote` (`contracts.py`); `ProvenancePanel` | Implementado; no staging |
| Valor ausente nunca é preenchido | Política de integridade | Variação sem base fica nula (`test_quote_change_day36.py`); tabela da comparação alinhada por instante (`day39-frontend.test.ts`) | Implementado; **não** no staging |
| Heatmap sem setor e valor de mercado inventados | [ADR-019](adr/019-global-atlas-table-and-basic-heatmap.md) | Contrato declara `INSTRUMENT_TYPE` e `EQUAL_AREA` | Implementado; **não** no staging |

## 3. Privacidade e dados pessoais

| Controle | Norma | Prova | Estado |
| --- | --- | --- | --- |
| Senha com Argon2id | [PROJECT_SPEC.md](PROJECT_SPEC.md) | `apps/api/app/auth/passwords.py` | Implementado; no staging |
| Sessão opaca em cookie `HttpOnly`, `Secure` em staging, `SameSite=lax` | PROJECT_SPEC.md; [ADR-008](adr/008-same-origin-api-proxy.md) | `routers.py` (cookie); `render.yaml`; `SameSite=none` recusado no boot | Implementado; no staging |
| Exclusão de conta por anonimização, com revogação de sessões e auditoria na mesma transação | [Runbook do Dia 28](operations/PRODUCTION_RUNBOOK_DAY_28.md) | `DELETE /api/v1/account`; `test_account_anonymization_day28.py` | Implementado; no staging |
| Anulação da nota livre dos eventos da carteira na anonimização | [ADR-010](adr/010-portfolio-event-note-erasure.md) | Migration `20261005_0012` | Implementado; **não** no staging |
| Exportação dos dados do usuário | Runbook do Dia 28 | `GET /api/v1/account/data-export` | Implementado; no staging |
| Retenção: expurgo de quarentenas, payloads brutos e telemetria após 90 dias; `audit_logs` nunca expurgado | Runbook do Dia 28 | `app/retention.py` (`PURGE_PLAN`); `python -m app.cli.retention` (dry-run por padrão) | Implementado; execução agendada inexistente |
| Telemetria sem dado pessoal, só agregados diários | Runbook do Dia 28 | `TelemetryPIIError` e `web_vital_metrics` (`app/telemetry.py`) | Implementado; no staging |
| **Aviso de privacidade e termos de uso para o usuário** | — | Nenhum documento publicado | **Lacuna:** exige avaliação jurídica antes de abrir o produto a outras pessoas |
| Seção de retenção do [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) | — | Dizia que a retenção "será definida"; adendo de 2026-10-07 aponta o que o Dia 28 implementou | Atualizada |

## 4. Segurança

| Controle | Norma | Prova | Estado |
| --- | --- | --- | --- |
| CSRF em todo método mutante | Runbook do Dia 28 | `CSRFMiddleware` | Implementado; no staging |
| CSRF avaliado antes do rate limit | [ADR-009](adr/009-csrf-before-rate-limit.md) | `test_middleware_order_day30.py` | Implementado; **não** no staging |
| Rate limit por IP; por usuário no balde `standard` | [ADR-017](adr/017-per-user-rate-limit.md) | `test_rate_limit_per_user_day35.py` | Implementado; **não** no staging |
| IP do cliente não forjável | [ADR-012](adr/012-untrusted-proxy-headers.md); [ADR-020](adr/020-trusted-proxy-hops.md) | `--no-proxy-headers` medido no staging; saltos confiáveis testados contra forja | ADR-012 no staging; ADR-020 **pendente de ativação** (H-23) |
| Cabeçalhos de segurança (CSP da API, HSTS, `X-Frame-Options`, `Referrer-Policy`) | Runbook do Dia 28 | `SecurityHeadersMiddleware` | Implementado; no staging |
| `/docs`, `/redoc` e `/openapi.json` fechados em staging e produção | Runbook do staging | `test_staging_day29.py`; smoke medido | No staging |
| Cadastro fechado em staging; convite antes de abrir | [ADR-011](adr/011-registration-by-invite.md) | Cadastro responde 404 no staging (medido) | Fechado no staging; **convite não implementado** |
| CSP do frontend | H-02 no [handoff](DAY29_HANDOFF.md) | — | **Pendente** |
| Segredos fora do repositório | `AGENTS.md`; [SECURITY.md](../SECURITY.md) | `.env.example` só com nomes; varredura de segredos antes de cada commit | Implementado |

## 5. Trilha de auditoria

| Evento | Onde fica | Estado |
| --- | --- | --- |
| Transições editoriais (quem, de que estado, para qual, quando) | `editorial_review_events` | Implementado; no staging |
| Versões editoriais imutáveis | Trigger `editorial_versions_append_only` (migration 0008) | Implementado; no staging |
| Anonimização de conta | `audit_logs`, na mesma transação | Implementado; no staging |
| Seed e reset do DEMO local | `audit_logs` (`entity_type='demo_seed'`) | Implementado (somente local) |

## 6. Acessibilidade

| Controle | Prova | Estado |
| --- | --- | --- |
| WCAG 2.2 AA automatizado em 11 rotas e nos dois temas | `apps/web/e2e/day36-wcag.spec.ts` (29 de 29 no Dia 39) | Implementado; **não** no staging |
| Informação não depende só de cor | [Relatório do Dia 36](design/ACCESSIBILITY_DAY_36.md) | Implementado |
| Leitor de tela e zoom de 200% | — | **Pendente: revisão humana** |

## 7. O que impede declarar o produto pronto para terceiros

1. Assinatura do H-13 e ADR do fluxo editorial (H-25).
2. Aviso de privacidade e termos de uso, com avaliação jurídica.
3. Convite implementado (ADR-011) e IP real ativado (ADR-020).
4. CI verde e rodadas oficiais (H-05) e deploy dos Dias 30 a 40.
5. Dataset `PUBLIC_APPROVED` para qualquer dado que não seja `DEMO`.
