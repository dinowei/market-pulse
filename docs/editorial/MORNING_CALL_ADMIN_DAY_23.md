# Morning Call público e administrativo — Dia 23

O Dia 23 implementa o CMS administrativo mínimo do Morning Call factual e o
histórico público de versões. O prompt direto do operador prevaleceu sobre a
linha anterior do roadmap que previa integração de infraestrutura externa; o
código foi implementado com PostgreSQL local e continua sem provider real,
notícias externas, IA, Stripe ou deploy. Esta nota é documental e não amplia o
escopo de produto aprovado.

## Papéis e workflow

Usuários possuem um papel persistido entre `USER`, `EDITOR`, `REVIEWER` e
`ADMIN`. O acesso administrativo é default deny: usuários comuns recebem 403 e
falhas ao consultar o papel são tratadas como `USER`.

O ciclo append-only é:

`DRAFT → UNDER_REVIEW → APPROVED → PUBLISHED → ARCHIVED`

Editores e administradores criam rascunhos, novas versões e enviam para revisão.
Revisores e administradores aprovam, publicam e arquivam. A publicação sempre
revalida os blocos com a política editorial; correções geram nova versão e não
mutam conteúdo publicado. Eventos de criação, correção e transição são
registrados em `editorial_review_events`.

## Contratos

Rotas administrativas protegidas:

- `GET/POST /api/v1/editorial/admin/posts`
- `GET /api/v1/editorial/admin/posts/{post_id}`
- `POST /api/v1/editorial/admin/posts/{post_id}/versions`
- `POST /api/v1/editorial/admin/posts/{post_id}/validate`
- `POST /api/v1/editorial/admin/posts/{post_id}/submit-review`
- `POST /api/v1/editorial/admin/posts/{post_id}/approve`
- `POST /api/v1/editorial/admin/posts/{post_id}/publish`
- `POST /api/v1/editorial/admin/posts/{post_id}/archive`

Rotas públicas retornam somente versões `PUBLISHED`:

- `GET /api/v1/editorial/posts/{slug}/versions`
- `GET /api/v1/editorial/posts/{slug}/versions/{version_number}`

O frontend administrativo usa exclusivamente os tipos gerados a partir do
OpenAPI e envia a sessão opaca em cookie HttpOnly com `credentials: include`.
Datas exibidas ao público são formatadas em `America/Sao_Paulo` (BRT).

## Fronteiras editoriais

Os cinco `ContentType` permitidos são `FACT`, `THIRD_PARTY_CONSENSUS`,
`CONDITIONAL_SCENARIO`, `RISK` e `LIMITATION`. `FACT` exige fonte; consenso e
cenários exigem atribuição, fontes e linguagem condicional conforme a política
canônica. Linguagem prescritiva, promessa de retorno, suitability e ordem de
compra/venda não são publicáveis. A interface mostra disclaimer factual e
informativo; não apresenta conteúdo como recomendação financeira.

O administrador usa formulário simples para campos estruturados. Editor rico,
IA, ingestão de notícias, notificações e publicação de provider financeiro real
permanecem fora deste dia.

## Lacunas controladas

Provisionamento inicial de papéis é interno ao banco e ainda não possui tela de
gestão. A operação deve ser auditada e autorizada separadamente antes de
qualquer exposição pública. A integração externa de Neon/Upstash anteriormente
listada no roadmap foi preservada como trabalho futuro, sem autorização de
serviços ou credenciais.
