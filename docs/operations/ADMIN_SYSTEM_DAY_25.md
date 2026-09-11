# Painel operacional interno — Dia 25

## Escopo

O painel interno está disponível em `GET /api/v1/admin/system` e na rota web
`/admin/system`. Ele é um diagnóstico agregado para operadores autorizados; não
é um console de dados financeiros, não altera estado de mercado e não produz
recomendação financeira.

## Controle de acesso e auditoria

- A sessão precisa ser válida e o usuário precisa ter o papel exato `ADMIN`.
- `USER`, `EDITOR` e `REVIEWER` recebem `403`.
- Ausência ou sessão inválida recebe `401` pela política de autenticação atual.
- Cada tentativa registra `view_admin_system`, `allowed` ou `denied` em
  `audit_logs`, vinculada ao `request_id` correlacionado pelo middleware.
- Falha ao registrar auditoria não libera acesso nem interrompe o diagnóstico;
  o erro de persistência nunca é devolvido ao cliente.

## Conteúdo exibido

O contrato sempre carrega `checked_at` por seção e exibe estado `ok`,
`degraded` ou `down` para PostgreSQL e Redis. Também agrega versão OpenAPI,
último refresh/backfills e erros sanitizados, governança de provider/dataset,
contagens de quarentena, locks ativos sem expor chaves, publicação editorial e
volumetria de usuários/carteiras.

Provider, dataset e licença só aparecem como `allowed` quando a combinação
exata está aprovada; qualquer ausência ou estado desconhecido permanece
`denied` (default deny). O painel não expõe URL, senha, token, cookie, stack
trace, payload bruto, chave Redis ou identificador pessoal desnecessário.

## Operação segura

1. Correlacione o `X-Request-ID` da resposta com os logs internos.
2. Investigue `down` e `degraded` pelo ambiente local autorizado e pelos logs
   agregados; não copie connection strings ou segredos para tickets.
3. Trate quarentena e locks como sinais operacionais, não como autorização para
   publicar dados ou alterar o ledger append-only.
4. O painel pode ser exercitado com `DEMO`, mas `DEMO` e acesso administrativo
   não concedem licença de redistribuição.

## Verificações do Dia 25

O gate inclui testes de contrato/RBAC/sanitização, migration `0010` em banco
local, OpenAPI e cliente TypeScript regenerados, Ruff, Pytest, lint, typecheck,
testes e build web, além de `git diff --check` e scan direcionado de segredos.
Nenhum provider real, dado real, Stripe, corretora, IA ativa, scraping, push ou
deploy faz parte deste dia.
