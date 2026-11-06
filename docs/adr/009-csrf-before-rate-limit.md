# ADR-009: CSRF antes do rate limit e cabeçalhos de segurança em toda resposta

- Status: Accepted
- Data: 2026-10-05
- Decisores: responsável técnico (Claude Code), com delegação explícita do operador do
  projeto para os itens do Dia 30 (H-09)

## Contexto

Em `apps/api/app/main.py` os middlewares são registrados em ordem inversa de execução.
Até o Dia 29, uma requisição passava por `RequestId → CORS → RateLimit → CSRF →
SecurityHeaders → rota`. Isso tinha três efeitos (H-09 e revisão do Dia 30):

1. **Requisição forjada consumia cota.** Um site malicioso pode fazer o navegador da
   vítima disparar POSTs com `Origin` não permitido; cada um contava no balde por IP
   da vítima antes de ser recusado, ajudando a negar serviço a ela.
2. **A recusa por CSRF dependia do Redis.** Nas rotas de autenticação o rate limit
   falha fechado: com o Redis indisponível, a resposta era 503 em vez do 403 do CSRF.
3. **Respostas 403 e 429 saíam sem cabeçalhos de segurança**, porque esses erros são
   produzidos por middlewares externos ao `SecurityHeadersMiddleware`.

## Decisão

Nova ordem de execução: `RequestId → SecurityHeaders → CORS → CSRF → RateLimit → rota`.

- O CSRF é uma verificação local, sem I/O, e passa a recusar requisições forjadas antes
  de qualquer acesso ao Redis e sem consumir cota.
- O rate limit continua protegendo o login: clientes que não são navegador, sem cookie
  de sessão, passam pelo CSRF (não são vetor de CSRF) e são contados normalmente, e um
  `Origin` permitido forjado por script também é contado.
- Os cabeçalhos de segurança passam a valer para toda resposta, inclusive 403, 429 e
  503 produzidos pelos middlewares.
- O limite em si não muda (5/60 s na autenticação, 30/60 s no balde standard).

## Alternativas consideradas

- Manter a ordem: rejeitada pelos três efeitos acima.
- Rate limit separado só para requisições recusadas pelo CSRF: complexidade sem ganho,
  porque a recusa já não custa I/O.

## Consequências positivas

- 403 de CSRF determinístico e independente do Redis.
- Forjar requisições a partir do navegador da vítima não esgota a cota dela.
- Cabeçalhos de segurança uniformes.

## Consequências negativas e riscos

- Um atacante pode enviar volume ilimitado de requisições com `Origin` proibido sem ser
  contado. O custo de cada uma é uma comparação em memória; proteção volumétrica é papel
  da plataforma (Render, Vercel), não deste limitador.

## Como revisar esta decisão

Revisar junto do H-19 (limite por sessão) e do H-23 (IP real atrás de proxy).
