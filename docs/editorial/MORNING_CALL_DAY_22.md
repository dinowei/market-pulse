# Morning Call factual — Dia 22

O Dia 22 cria a fronteira editorial factual do Market Pulse. O prompt direto do
operador prevaleceu sobre qualquer descrição anterior: o código foi validado e
esta entrega não amplia o escopo aprovado.

## Contrato

Blocos publicáveis usam exatamente `FACT`, `THIRD_PARTY_CONSENSUS`,
`CONDITIONAL_SCENARIO`, `RISK` ou `LIMITATION`. O ciclo editorial é
`DRAFT → UNDER_REVIEW → APPROVED → PUBLISHED → ARCHIVED`; somente `PUBLISHED`
aparece nas rotas públicas.

`FACT` exige fonte. Consenso exige fonte e atribuição. Cenário exige linguagem
condicional e incerteza. Linguagem prescritiva, sinais, promessa de retorno e
orientação personalizada são bloqueados em contexto; termos factuais como
“vendas reportadas” permanecem permitidos.

Cada bloco preserva fontes e limitações. Dados financeiros relacionados mantêm
provider, dataset, `DataLevel`, `Freshness`, timestamps e restrições conforme as
políticas canônicas. `DEMO`, acesso interno ou autenticação administrativa não
concedem licença.

## Persistência e API

As tabelas `editorial_posts`, `editorial_post_versions` e `editorial_sources`
armazenam versões e proveniência. Versões são append-only no banco; correções
criam nova versão e nenhum endpoint de publicação altera uma versão existente.

- `GET /api/v1/editorial/morning-call/latest`
- `GET /api/v1/editorial/posts`
- `GET /api/v1/editorial/posts/{slug}`

As rotas são públicas somente para leitura de conteúdo publicado e retornam
`404` quando não há publicação elegível. Não há CMS/editor visual, IA, scraping,
notícias externas, provider financeiro real, notificações ou Stripe nesta etapa.

## Limitações e próximo gate

O beta usa apenas conteúdo inserido por fluxo administrativo interno e fixtures
sintéticas quando necessário. A implementação de uma interface administrativa,
licenciamento de fontes de notícias e integração de conteúdo externo exigem
autorização e documentação próprias. O próximo dia deve tratar o fluxo de
Global Atlas/dashboard conforme o roadmap, sem transformar conteúdo em
recomendação.
