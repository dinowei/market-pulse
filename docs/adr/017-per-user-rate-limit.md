# ADR-017: Limite de requisições por usuário nas rotas autenticadas (H-19)

- Status: Accepted
- Data: 2026-10-07
- Decisores: responsável técnico (Claude Code), com autorização do operador para executar
  o Dia 35 da Fase 2
- Relação: resolve H-19 do [handoff](../DAY29_HANDOFF.md); mantém a ordem de middlewares
  da [ADR-009](009-csrf-before-rate-limit.md) e o IP confiável da
  [ADR-012](012-untrusted-proxy-headers.md)

## Contexto

O balde `standard` (30 requisições por 60 s) era contado por IP. Usuários atrás do mesmo
NAT dividiam a mesma cota. O middleware de rate limit roda antes da autenticação da rota,
então não sabia quem era o usuário.

## Decisão

1. **Só o balde `standard` muda.** Os baldes `auth`, `public` e `telemetry` continuam por
   IP e com os mesmos limites.
2. **Chave por usuário quando a sessão é válida.** O middleware lê o cookie de sessão e o
   valida no mesmo serviço de autenticação da rota (`AuthService.me`). Com sessão válida,
   a chave é `rate_limit:standard:user:<id>`. A chave usa o id do usuário, não o token,
   para que abrir várias sessões não multiplique a cota.
3. **Qualquer outra situação usa o IP.** Sem cookie, com cookie forjado, sessão expirada
   ou revogada, ou falha no serviço de sessão, a chave é `rate_limit:standard:ip:<addr>`.
   Um cookie inventado não compra cota nova.
4. **Sem leitura dupla.** O usuário validado fica em `request.state.authenticated_user`,
   e `get_current_user` o reaproveita. A sessão é lida uma vez por requisição.
5. **O limite não foi relaxado:** continua 30 por 60 s, agora por pessoa.

## Consequências

- Requisições ao balde `standard` com cookie fazem uma leitura de sessão antes da decisão
  de limite, inclusive as que terminam em 429. Antes, a rota já fazia essa leitura nas
  requisições aceitas; o custo extra fica nas recusadas.
- A falha do serviço de sessão cai no IP e não derruba a requisição no middleware; a
  rota mantém o tratamento de erro que já tinha.
- Todas as chaves ganharam o prefixo do sujeito (`ip:` ou `user:`). No deploy, os
  contadores antigos deixam de ser lidos e expiram sozinhos ao fim da janela; os baldes
  recomeçam do zero uma vez.
- **Achado de leitura de código (H-24, para o Dia 39):** `get_auth_service()` cria um
  `AuthService` novo a cada chamada, e cada um abre clientes Redis próprios. Isso já
  acontecia antes desta ADR; um pool compartilhado por processo é a correção.

## Evidência

`apps/api/tests/test_rate_limit_per_user_day35.py`: dois usuários no mesmo IP não dividem
o balde; o limite de cada um continua valendo; cookie forjado, sessão revogada e
requisição anônima caem no balde do IP; a sessão é lida uma vez por requisição.
`apps/api/tests/test_rate_limit_buckets_day28.py` foi atualizado para as chaves com
prefixo `ip:`.
