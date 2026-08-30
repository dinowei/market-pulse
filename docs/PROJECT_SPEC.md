# Market Pulse — Especificação consolidada do MVP beta

- **Status:** Aprovado para planejamento; implementação por dias depende de autorização
- **Data:** 2026-08-30
- **Horizonte:** 30 dias corridos
- **Execução:** uma pessoa usando intensivamente o Codex

## Convenção de evidência

- **Fato:** observado no repositório ou confirmado pelo operador.
- **Decisão:** escolha aprovada para o MVP.
- **Hipótese:** premissa que ainda precisa de validação.
- **Pendência:** trabalho ou informação necessária posteriormente.

## Visão do produto

**Decisão:** O Market Pulse será um terminal web autenticado e informativo de acompanhamento de mercados. Ele exibirá dados atribuídos e datados, watchlist, heatmap, Morning Call e estado de saúde dos providers.

**Decisão:** O produto nunca apresentará recomendação de compra/venda, timing, alocação, preço-alvo próprio, promessa de resultado ou orientação personalizada.

> Conteúdo informativo. Não constitui recomendação de investimento.

## Universo inicial

**Decisão:** O beta cobrirá componentes selecionados do Ibovespa para o heatmap; dez ações americanas; Ibovespa, S&P 500 e Nasdaq; USD/BRL; ouro, Brent e WTI.

**Pendência:** A lista nominal dos componentes brasileiros e das dez ações americanas será fechada antes do primeiro adapter real.

**Decisão:** O heatmap usará área por valor de mercado e cor pela variação percentual diária, agrupado por setor, com alternativa acessível em tabela/lista.

## Funcionalidades do MVP

1. Dashboard responsivo em tema escuro.
2. API própria e versionada em `/api/v1`.
3. PostgreSQL como fonte persistente; Redis como cache/lock.
4. Provider adapters substituíveis e fallback por ativo.
5. Metadados de fonte, timestamps, nível do dado e `fresh`/`stale`.
6. Heatmap/treemap setorial.
7. E-mail/senha e sessão opaca em cookie `HttpOnly`.
8. Watchlist persistida por usuário.
9. Morning Call armazenado, versionado e exibido.
10. Comando administrativo interno para Morning Call, sem editor visual e sem IA.
11. Testes essenciais, documentação e artefatos de deploy.

## Arquitetura aprovada

**Decisão:** Monorepo e monólito modular com Next.js/TypeScript/Tailwind em `apps/web`; FastAPI, SQLAlchemy 2 e Alembic em `apps/api`; PostgreSQL; Redis; OpenAPI; e providers atrás de interfaces.

**Decisão:** Refresh usa processo curto com o código da API, acionado futuramente por scheduler externo/gerenciado, sem daemon permanente no beta.

**Decisão:** O frontend é preparado para Vercel. Backend, job, PostgreSQL e Redis serão preparados para serviços compatíveis, sem login, provisionamento ou publicação sem autorização posterior.

## Dados financeiros

Cada item deve informar `source`, `source_timestamp`, `fetched_at`, `data_level`, `freshness`, motivo quando stale e limitação aplicável. `data_level` aceita `REAL_TIME`, `DELAYED`, `EOD` ou `DEMO`.

**Decisão:** Um dado só substitui o último snapshot se símbolo, bolsa, moeda, número e timestamp forem válidos.

**Decisão:** Em falha, o fallback por ativo tenta cache expirado validado e depois PostgreSQL. Sem snapshot válido, o ativo fica indisponível; nenhum valor é inventado.

## Providers e licenças

**Decisão:** Priorizar fontes gratuitas ou delayed compatíveis com demonstração pública, sem contratar planos nem presumir redistribuição.

**Decisão:** Apenas `PUBLIC_COMMERCIAL` alimenta respostas públicas. `PERSONAL_ONLY`, `DEMO_LIMITED` e `INTERNAL_FALLBACK_ONLY` são bloqueados pela regra de domínio.

**Fato:** Nenhuma licença de provider foi validada documentalmente no Dia 1.

**Pendência:** Validar documentação oficial, atribuição, quotas, delay, cobertura, redistribuição e preço antes de selecionar adapter real.

## Conteúdo financeiro e Morning Call

**Decisão:** Tipos permitidos: `FACT`, `THIRD_PARTY_CONSENSUS`, `CONDITIONAL_SCENARIO`, `RISK` e `LIMITATION`.

**Decisão:** Fluxo: rascunho → validação automática → revisão humana → publicação versionada.

**Decisão:** Publicações são append-only. Correções criam nova versão com referência, timestamp e motivo; `UPDATE`/`DELETE` serão bloqueados quando o módulo for implementado.

## Identidade e sessão

**Decisão:** Cadastro por e-mail/senha, Argon2, sessão opaca aleatória, cookie `HttpOnly`, `Secure` em produção e `SameSite=Lax` por padrão.

Fora do mês: recuperação de senha, MFA, login social e verificação de e-mail.

## Fora do escopo dos 30 dias

- Stripe, billing, assinatura, paywall e planos pagos.
- WhatsApp, Telegram, e-mail, push e alertas.
- Chat, insights ou texto gerado por IA.
- Recomendações, sinais, preço-alvo, suitability ou promessas.
- Apps móveis, corretoras, ordens, carteira, P&L e backtesting.
- WebSockets/tick streaming, microserviços, Kafka, Kubernetes e alta disponibilidade.
- CMS visual, watchlists compartilhadas e integrações não essenciais.
- Deploy externo ou serviço pago sem autorização posterior.

## Pendências controladas

- Lista nominal de ativos.
- Licenças e termos de exposição pública dos providers.
- Freshness por classe e horário de mercado.
- Taxonomia setorial e fonte de market cap.
- Owner GitHub real para ativar CODEOWNERS.
- Canal privado de reporte de segurança.
- Plataforma autorizada para backend, job, PostgreSQL e Redis.
