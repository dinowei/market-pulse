# Market Pulse — especificação consolidada do MVP beta

- **Status:** Aprovado para execução pelo roadmap; cada dia depende de autorização
- **Data:** 2026-08-30
- **Horizonte:** 30 dias corridos
- **Execução:** uma pessoa usando intensivamente o Codex

## Convenção de evidência

- **Fato:** observado no repositório ou confirmado pelo operador.
- **Decisão:** escolha aprovada para o MVP.
- **Hipótese:** premissa que ainda precisa de validação.
- **Pendência:** trabalho ou informação necessária posteriormente.

## Visão e limites do produto

**Decisão:** O Market Pulse é um terminal web autenticado, informativo e analítico para acompanhamento de mercados. Exibe dados atribuídos e datados, dashboard, watchlist, heatmap, Global Atlas, Morning Call e saúde dos providers.

**Decisão:** O produto não oferece recomendação de compra/venda/manutenção, sinal, timing, alocação, preço-alvo próprio, promessa de resultado, suitability, análise personalizada ou execução financeira.

> **Conteúdo informativo. Não constitui recomendação de investimento.**

## Universo inicial

**Decisão:** O beta cobrirá componentes selecionados do Ibovespa para o heatmap; dez ações americanas; Ibovespa, S&P 500 e Nasdaq; USD/BRL; ouro, Brent e WTI.

**Pendência:** A lista nominal dos componentes brasileiros e das dez ações americanas será fechada antes do primeiro adapter real.

**Decisão:** O heatmap usará área por valor de mercado, cor pela variação percentual diária e agrupamento por setor. Uma tabela/lista equivalente será sempre oferecida.

## Escopo funcional P0

1. Dashboard financeiro responsivo em tema escuro.
2. Particle Atlas P0 como sistema visual, de interação e apresentação de dados.
3. Global Atlas P0 em tabela acessível; visual geográfico avançado não é requisito.
4. API própria e versionada em `/api/v1` com OpenAPI.
5. PostgreSQL como fonte persistente; Redis como cache/lock não autoritativo.
6. Provider adapters substituíveis, license gate e fallback por ativo.
7. Fonte, timestamps, latência/nível do dado, `Freshness` e limitações visíveis.
8. Heatmap/treemap setorial com alternativa acessível.
9. Cadastro por e-mail/senha e sessão opaca em cookie `HttpOnly`.
10. Watchlist persistida e isolada por usuário.
11. Morning Call armazenado, versionado, revisado e exibido.
12. Comando administrativo interno para Morning Call, sem editor visual e sem IA.
13. Testes essenciais, documentação, observabilidade e artefatos de deploy.

## Particle Atlas

**Decisão:** Particle Atlas é o sistema visual, de interação e apresentação de dados do frontend. É informativo e analítico; não é provider, motor de análise/recomendação/predição, promessa de tempo real nem substituto de proveniência.

O P0 inclui:

- design system escuro técnico, tokens e componentes reutilizáveis;
- layout responsivo, dashboard, cards e estados de loading, vazio, erro, `STALE` e `UNAVAILABLE`;
- fonte, horário, atraso, `DataLevel`, `Freshness`, limitações e disclaimer visíveis;
- heatmap/treemap e Global Atlas com tabela equivalente;
- Morning Call e watchlist;
- navegação por teclado, foco perceptível, WCAG 2.2 AA e `prefers-reduced-motion`;
- semântica que nunca dependa somente de cor.

Convenção cromática: verde para variação positiva, vermelho para negativa, âmbar para `STALE`/operação, violeta para `DEMO` e cinza para `UNAVAILABLE`. Texto, ícone ou padrão deve repetir o significado.

**P1 condicional:** partículas, ondas, transições avançadas, Canvas/WebGL, profundidade, animações de conexão e globo 3D leve. Exigem P0 verde, feature flag, fallback, movimento reduzido e orçamento de desempenho; não bloqueiam o beta.

## Arquitetura aprovada

**Decisão:** Monorepo e monólito modular com Next.js App Router/React/TypeScript strict/Tailwind em `apps/web`; FastAPI, SQLAlchemy 2 e Alembic em `apps/api`; PostgreSQL; Redis; OpenAPI; e providers atrás de interfaces.

**Decisão:** Refresh usa processo curto, idempotente e compartilhado com o domínio da API. O alvo de agendamento é GitHub Actions cron chamando endpoint interno protegido, sem daemon permanente no beta.

**Decisão:** Desenvolvimento usa Docker Compose local. Destinos pretendidos, ainda não provisionados, são Vercel para web, Render para API, Neon PostgreSQL e Upstash Redis REST.

Nenhum login, serviço, segredo, contratação, deploy ou cobrança externa está autorizado pelo documento.

## Dados financeiros e resiliência

Cada item deve informar `source`, `source_timestamp`, `fetched_at`, `DataLevel`, `Freshness`, motivo quando stale e limitação aplicável.

`DataLevel` aceita exatamente:

- `REAL_TIME`
- `DELAYED`
- `EOD`
- `DEMO`

`Freshness` aceita exatamente:

- `FRESH`
- `STALE`
- `UNAVAILABLE`

Os conceitos são independentes. `REAL_TIME` só pode ser alegado com comprovação técnica e contratual; `DEMO` nunca implica licença.

**Decisão:** Um dado só substitui o último snapshot quando símbolo, bolsa, moeda, número, timestamps e regras de qualidade forem válidos.

**Decisão:** Em falha, o fallback por ativo tenta cache expirado validado e PostgreSQL. O último valor válido é mostrado como `STALE`, com motivo e timestamp. Sem snapshot válido, fica `UNAVAILABLE`; nenhum valor é inventado.

## Providers e licenças

**Decisão:** Priorizar fontes gratuitas ou delayed compatíveis com demonstração pública, sem contratar planos nem presumir redistribuição.

**Decisão:** Licenciamento é default deny por provider, plano, endpoint, dataset, finalidade e modalidade. Estados operacionais permitidos: `UNREVIEWED`, `REJECTED`, `DEVELOPMENT_ONLY` e `PUBLIC_APPROVED`.

Somente a combinação exata com `PUBLIC_APPROVED` e evidência vigente pode alimentar resposta pública. `DEMO`, autenticação administrativa, feature flag, allowlist e acesso interno não concedem direitos.

**Fato:** Nenhuma licença externa foi aprovada documentalmente no Dia 1. Os candidatos permanecem `UNREVIEWED` na [matriz operacional](DATA_PROVIDER_LICENSE_MATRIX.md).

## Conteúdo financeiro e Morning Call

**Decisão:** Tipos permitidos exatamente: `FACT`, `THIRD_PARTY_CONSENSUS`, `CONDITIONAL_SCENARIO`, `RISK` e `LIMITATION`.

**Decisão:** Fluxo normativo: `DRAFT` → `VALIDATION_FAILED` ou `VALIDATED` → `IN_REVIEW` → `PUBLISHED` → `SUPERSEDED`.

Revisão humana é obrigatória. Publicações são append-only; correções criam nova versão com referência, timestamp e motivo. A [política canônica](policies/FINANCIAL_CONTENT_POLICY.md) prevalece para limites editoriais.

Morning Call é inserido por comando administrativo interno. Não há editor visual, IA, recomendação ou publicação automática.

## Identidade e sessão

**Decisão:** Cadastro por e-mail/senha com Argon2id, sessão opaca aleatória e cookie `HttpOnly`, `Secure` em produção e `SameSite=Lax` por padrão. Logout, expiração, revogação, Origin/CSRF e autorização por usuário devem ser testados.

Fora do mês: recuperação de senha, MFA, login social e verificação de e-mail.

## Stripe no beta

**Decisão posterior e explícita:** Stripe pode ser preparado somente em modo de teste, isolado e opcional, após o P0 principal. Não haverá cobrança real, plano comercial ativo, contratação ou dependência do fluxo financeiro principal. A integração depende da autorização do dia correspondente.

## Fora do escopo dos 30 dias

- Stripe em produção, cobrança real, assinatura comercial, paywall e planos pagos.
- WhatsApp, Telegram, e-mail, push, alertas e notificações.
- Chat, conteúdo/insights produzidos por IA, recomendações, sinais e preço-alvo próprio.
- Apps móveis, corretoras, ordens, carteira, P&L e backtesting.
- WebSockets/tick streaming, microserviços, Kafka, Kubernetes e alta disponibilidade.
- CMS/editor visual, watchlists compartilhadas e integrações não essenciais.
- Globo 3D, Canvas/WebGL, partículas e animações avançadas como bloqueadores do beta.
- Deploy externo, contratação ou serviço pago sem autorização posterior.

## Pendências controladas

- Lista nominal de ativos.
- Revisão oficial de licenças e termos por combinação de uso.
- Janelas de freshness por classe e horário de mercado.
- Taxonomia setorial e fonte licenciada de market cap.
- Canal privado definitivo para reporte de segurança.
- Autorização futura para contas/projetos Vercel, Render, Neon, Upstash e Stripe test mode.
- Orçamento de desempenho que decidirá se algum item P1 do Particle Atlas entra no beta.
