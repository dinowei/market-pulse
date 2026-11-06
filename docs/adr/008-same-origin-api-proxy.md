# ADR-008: API servida pela mesma origem do web via proxy do Next.js

- Status: Accepted
- Data: 2026-10-05
- Decisores: responsável técnico (Claude Code), com delegação explícita do operador do
  projeto em 2026-10-05 para decidir os bloqueadores do Dia 29

## Contexto

O staging privado do Dia 29 roda o web na Vercel (`*.vercel.app`) e a API no Render
(`*.onrender.com`). São sites diferentes. O frontend chama a API direto do navegador com
`credentials: "include"`, e o cookie de sessão é `HttpOnly`, `Secure` fora de
`local`/`test` (`routers.py`, login) e `SameSite=lax` (`config.py`). Um cookie `Lax` não
é enviado em `fetch` entre sites: o login responderia 200, mas a sessão não seria enviada
nas requisições seguintes. As alternativas avaliadas no Dia 29 foram:

- **A. Domínio próprio** com subdomínios para web e API: resolve, mas tem custo
  recorrente, exige registro e DNS fora do repositório, e o preço não foi verificado.
- **B. Proxy same-origin no Next.js**: o navegador fala só com a origem do web; a Vercel
  repassa `/api/v1/*` para a API.
- **C. `SameSite=None; Secure`**: afrouxa a política de cookie e continua quebrando em
  navegadores que bloqueiam cookies de terceiros.

## Decisão

Adotar a opção **B**.

- `apps/web/next.config.ts` registra o rewrite `/api/v1/:path*` → `<origem>/api/v1/:path*`
  somente quando `MARKET_PULSE_API_PROXY_ORIGIN` está definida. A variável é só de servidor
  (sem prefixo `NEXT_PUBLIC_`) e precisa ser uma origem `https` sem caminho, credencial,
  query ou fragmento; um valor inválido falha o build (`src/lib/api-proxy.ts`).
- No staging, `NEXT_PUBLIC_API_BASE_URL` aponta para a **própria origem do web**, então
  o código dos componentes não muda e o cookie fica first-party na origem do web.
- Em `production`/`staging` a API recusa `MARKET_PULSE_AUTH_COOKIE_SAMESITE` diferente
  de `lax` ou `strict` (`validate_production_settings`). A opção C fica bloqueada por
  código, não só por documentação.
- Desenvolvimento local continua chamando a API diretamente (variável ausente = sem proxy).

## Alternativas consideradas

- A: válida para produção pública futura; reavaliar quando houver domínio.
- C: rejeitada, porque reduz a proteção do cookie e depende de navegador.

## Consequências positivas

- Sem custo e sem cookie de terceiros.
- O CSRF por `Origin` continua valendo: o navegador envia a origem do web, que precisa
  estar em `MARKET_PULSE_CORS_ORIGINS`.
- A troca futura para domínio próprio não exige mudar os componentes.

## Consequências negativas e riscos

- Cada chamada passa pela Vercel e conta nos limites do plano Hobby, que é restrito a uso
  pessoal e não comercial (H-07).
- **IP do cliente:** a API identifica o cliente por `request.client.host`. Atrás do proxy
  do Render, e ainda mais atrás da Vercel, esse valor tende a ser o do intermediário, e o
  rate limit por IP vira um balde compartilhado. Isso é aceitável num staging de um único
  usuário e **obrigatório de resolver antes de abrir o produto** (H-23).
- Previews da Vercel têm URLs próprias que não estão em `MARKET_PULSE_CORS_ORIGINS`; só o
  deployment de produção do projeto web é suportado no staging.
- Que o proxy da Vercel repassa `Cookie`, `Set-Cookie` e `Origin` sem alteração é
  **suposição** a validar no primeiro deploy (runbook do Dia 29, smoke de sessão).

## Como revisar esta decisão

Revisar ao adotar domínio próprio, ao abrir o produto a outras pessoas, ou se o smoke de
sessão do staging falhar.
