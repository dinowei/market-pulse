# Autenticação e sessões opacas — Dia 18

O Dia 18 cria a fronteira de identidade do Market Pulse para os recursos
privados futuros. As rotas públicas de instrumentos, quotes e histórico não
exigem sessão; watchlists e carteiras usarão a dependência de usuário atual nos
Dias 19 e 20.

## Endpoints

- `POST /api/v1/auth/register` cria usuário com e-mail normalizado.
- `POST /api/v1/auth/login` valida credenciais e emite cookie opaco.
- `POST /api/v1/auth/logout` revoga a sessão e expira o cookie.
- `GET /api/v1/auth/me` retorna somente `id`, `email` e `status`.

Respostas de erro usam Problem Details, mensagens genéricas e `request_id`.
Login falho não revela se o e-mail existe; o fluxo executa verificação dummy
quando necessário.

## Senha e sessão

Senhas são derivadas com Argon2id (`argon2-cffi`), com `time_cost=3`,
`memory_cost=65536` e `parallelism=2`. Nenhuma senha ou hash aparece em JSON,
logs ou cookies. A sessão usa `secrets.token_urlsafe(48)`; apenas o SHA-256 do
token é usado como chave lógica no Redis. O token puro nunca é persistido,
retornado em JSON ou exposto ao JavaScript.

O Redis guarda a sessão com TTL configurável (`MARKET_PULSE_AUTH_SESSION_TTL_SECONDS`).
O cookie padrão é `market_pulse_session`, `HttpOnly`, `SameSite=Lax`, `Path=/`
e `Secure` fora dos ambientes `local`/`test`. Logout remove a chave e envia
deleção do cookie. Redis indisponível falha fechado com `503` em fluxos que
precisam criar ou ler sessão.

## Rate limit e isolamento

Login e registro usam contador por IP no Redis, com janela e máximo configuráveis
(`MARKET_PULSE_AUTH_RATE_LIMIT_WINDOW_SECONDS` e
`MARKET_PULSE_AUTH_RATE_LIMIT_MAX_ATTEMPTS`). Falha do limitador não libera
acesso. A dependência `get_current_user` valida o cookie no backend e será a
base para owner checks; o Dia 18 não implementa watchlist ou carteira.

JWT não foi adotado porque o beta precisa de revogação imediata, estado
controlado no servidor e menor superfície de exposição. Middleware frontend,
se usado no futuro, será apenas uma conveniência de redirecionamento; a
autorização definitiva permanece na API.

## Limites conscientes

Não há recuperação de senha, MFA, verificação de e-mail, OAuth/login social,
envio de e-mail, Stripe, integração com corretora ou provider financeiro real.
As telas `/login` e `/register` enviam credenciais com `credentials: "include"`
e não usam `localStorage`/`sessionStorage`; o cookie HttpOnly não é lido pelo
browser. Persistência adicional na tabela `sessions` existente fica reservada
para uma decisão posterior; o store ativo deste dia é Redis com TTL.
