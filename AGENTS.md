# Market Pulse — instruções operacionais do repositório

## Hierarquia documental

Em caso de conflito, siga nesta ordem:

1. instrução direta e atual do operador;
2. este `AGENTS.md`;
3. `AGENTS.md` aplicável no subdiretório;
4. [especificação do produto](docs/PROJECT_SPEC.md);
5. [política canônica de conteúdo financeiro](docs/policies/FINANCIAL_CONTENT_POLICY.md);
6. [política de integridade de dados financeiros e carteiras](docs/policies/FINANCIAL_DATA_AND_PORTFOLIO_INTEGRITY_POLICY.md);
7. [roadmap canônico](docs/ROADMAP_30_DAYS.md);
8. [arquitetura canônica](docs/ARCHITECTURE.md);
9. ADRs aceitas em `docs/adr/`.

Uma fonte inferior não pode ampliar autorização concedida por uma fonte superior. Divergência material com ADR aceita exige nova ADR; não edite a decisão histórica silenciosamente.

## Workspace e limites

- Trabalhe somente na raiz Git aberta deste repositório.
- Não acesse, copie ou altere o FraudShield nem outro projeto.
- Preserve alterações preexistentes e confira `git status`/diff antes e depois.
- Não avance para outro dia ou subtarefa sem autorização explícita.
- Não faça deploy, login externo, contratação, provisionamento, push ou publicação sem autorização específica.
- Não apague, mova, renomeie ou reescreva histórico sem autorização específica.

## Execução por dia

Antes de alterar, confirme workspace, branch, persistência do Git, dia autorizado, dependências e critérios de aceite. Apresente um plano curto. Execute somente o menor conjunto de mudanças necessário e pare no gate do dia.

Cada dia do [roadmap](docs/ROADMAP_30_DAYS.md) tem gate próprio. Um gate só passa com evidência reproduzível; ausência de ferramenta ou ambiente deve ser registrada como pendência, nunca tratada como sucesso.

## Segurança e segredos

- Nunca grave chave, token, senha, cookie, dado pessoal, conexão real ou conteúdo de credencial.
- Apenas `.env.example` pode ser versionado, com nomes e valores vazios ou inequivocamente fictícios.
- `.env`, `.env.*`, `credentials.json`, chaves privadas e arquivos equivalentes devem permanecer ignorados.
- Não exponha body bruto de provider, stack trace, segredo ou identificador sensível em erro ou log.
- Revise o diff por segredos antes de cada commit.
- Siga [SECURITY.md](SECURITY.md); não publique vulnerabilidades exploráveis.

## Dados financeiros e licenciamento

- Não invente cotação, fonte, endpoint, quota, latência, licença ou permissão.
- Providers devem ficar atrás de interfaces substituíveis.
- Licenciamento é `default deny` por provider, plano, endpoint, dataset, finalidade e modalidade de uso.
- `DEMO`, autenticação administrativa, feature flag ou acesso interno não concedem direitos de licença.
- Nenhum provider/dataset pode alimentar exposição pública sem status `PUBLIC_APPROVED` e evidência documental aplicável na [matriz de licenças](docs/DATA_PROVIDER_LICENSE_MATRIX.md).
- Todo dado exibido deve preservar fonte, timestamps, `DataLevel`, `Freshness` e limitações.
- `DataLevel` e `Freshness` são conceitos separados. Nunca descreva `DELAYED`, `EOD`, `DEMO` ou `STALE` como tempo real/atual.
- Fallback usa apenas último snapshot validado e o marca `STALE`; sem valor válido, use `UNAVAILABLE`.

## Conteúdo financeiro

Obedeça integralmente à [política canônica](docs/policies/FINANCIAL_CONTENT_POLICY.md). O produto é informativo e analítico, nunca recomendação de investimento. São proibidos sinais, imperativos de compra/venda, preço-alvo próprio, promessa de retorno, suitability e aconselhamento personalizado.

Morning Call é criado por comando administrativo interno, validado automaticamente, revisado por humano e publicado de forma versionada e append-only. IA, editor visual e publicação automática estão fora do beta.

## Particle Atlas e acessibilidade

Particle Atlas é o sistema visual, de interação e apresentação de dados do frontend; não é provider nem motor de recomendação. O núcleo P0 deve manter proveniência, horário, latência, `DataLevel`, `Freshness`, limitações e indisponibilidade visíveis.

WCAG 2.2 AA, navegação por teclado, foco perceptível, alternativa textual/tabular, `prefers-reduced-motion` e semântica que não dependa somente de cor são requisitos. Partículas, Canvas/WebGL, transições avançadas e globo 3D são P1 condicionais, feature-flagged, com fallback e nunca bloqueiam o beta.

## Arquitetura e código futuro

- Preserve o monólito modular, a API versionada em `/api/v1` e OpenAPI como contrato.
- Modelos HTTP, domínio, persistência e payloads de provider são camadas distintas.
- PostgreSQL é a fonte persistente; Redis é cache/lock não autoritativo.
- Jobs devem ser curtos, idempotentes e usar o mesmo código de domínio da API.
- Use UTC internamente e zonas explícitas na apresentação.
- Evite microserviços, streaming, filas e abstrações de alta escala sem evidência e ADR.
- Quando houver código, prefira testes determinísticos e sem rede real no CI.

## Dependências e ferramentas

- Não instale ou atualize dependências fora do dia autorizado.
- Antes de fixar versão, verifique fonte oficial e registre a evidência/compatibilidade.
- Não adicione SDK de provider, Stripe ou serviço externo antes do respectivo gate.
- Prefira lockfiles, comandos não interativos e configuração mínima revisável.

## Git, commits e revisão

- Use Conventional Commits e commits pequenos por unidade lógica.
- Nunca use `git add .`; faça staging por caminhos explícitos.
- Antes de cada commit, revise arquivos staged, diff staged, whitespace, segredos, código inesperado e verificações aplicáveis.
- Não use comandos destrutivos nem reescreva histórico compartilhado.
- Não faça commit, push ou merge quando a autorização limitar a tarefa antes desses atos.
- Use [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) e respeite [.github/CODEOWNERS](.github/CODEOWNERS).

## Definition of Done

Uma tarefa só está concluída quando:

- escopo, dia e dependências autorizados foram respeitados;
- critérios de aceite possuem evidência reproduzível;
- testes, lint, typecheck e build aplicáveis passaram;
- documentação, política e ADRs permanecem consistentes;
- acessibilidade foi verificada quando houver interface;
- segurança, privacidade, licenciamento, proveniência e fallback foram avaliados;
- migração e rollback foram registrados quando aplicáveis;
- nenhum segredo, dado pessoal, código ou arquivo fora do escopo entrou no diff;
- `git status`, diff completo e comandos/exit codes foram revisados;
- riscos e pendências reais foram declarados.

Consulte [docs/AGENTS.md](docs/AGENTS.md) para regras complementares de manutenção documental.

## Baseline enterprise

Sempre que a tarefa envolver backend, frontend, banco, API, testes, infraestrutura, segurança, contratos, providers, jobs, autenticação, CI ou integração entre módulos, leia docs/engineering/ENTERPRISE_ENGINEERING_BASELINE.md antes de alterar arquivos.

Sempre que a tarefa envolver cotações, histórico, FX, dados de mercado, providers, carteiras, rentabilidade, P&L, TWR, gráficos financeiros, Morning Call ou exibição de preço, leia docs/policies/FINANCIAL_DATA_AND_PORTFOLIO_INTEGRITY_POLICY.md antes de alterar arquivos.

Para mudanças no CI ou supply chain, consulte também `docs/engineering/WEEK_1_GATE.md`.

- Tarefas de frontend também exigem a leitura de `docs/design/PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md`.
- Consulte o `AGENTS.md` local de `apps/api` ou `apps/web` quando existir.
- O OpenAPI e o cliente gerado são contratos; não altere o cliente gerado manualmente.

<!-- PARTICLE_ATLAS_FRONTEND_ROUTING:START -->

Mandatory Particle Atlas frontend contract

Before planning, reviewing or modifying apps/web/**, financial charts, visual data, frontend-consumed OpenAPI contracts, portfolio performance, responsive behavior, accessibility or frontend data states, read in full:

docs/design/PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md;

docs/policies/FINANCIAL_CONTENT_POLICY.md;

docs/ROADMAP_30_DAYS.md;

relevant ADRs, especially ADR-005, ADR-006 and ADR-007;

the current OpenAPI contract and generated frontend types.

Treat the directive as binding within its scope. The UI is predominantly black, white and gray; gold is not an identity or focus color. Market direction is green for UP, red for DOWN and blue for FLAT, always with a non-color cue. One real series produces one financial line. Multi-series comparisons default to INDEX_100 while preserving actual values, currency, provenance and timestamps.

Never invent endpoints, fields, market data, points, relationships or recommendations to satisfy a design. If design, policy, roadmap and backend conflict, stop and report the conflict, impact and safe options before changing code.

Cláudio owns visual direction; Codex owns implementation quality and backend integration; the human product owner approves the result. P1 visuals never delay or silently enter P0.

<!-- PARTICLE_ATLAS_FRONTEND_ROUTING:END -->
