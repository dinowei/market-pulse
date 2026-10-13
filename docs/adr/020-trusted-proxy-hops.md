# ADR-020: Endereço do cliente por saltos de proxy confiáveis (H-23)

- Status: Accepted (mecanismo); ativação no staging **pendente de medição**
- Data: 2026-10-07
- Decisores: responsável técnico (Claude Code), com autorização do operador para executar
  o Dia 39 da Fase 2
- Relação: completa a [ADR-012](012-untrusted-proxy-headers.md) sem alterá-la; afeta os
  limites da [ADR-009](009-csrf-before-rate-limit.md) e da
  [ADR-017](017-per-user-rate-limit.md)

## Contexto

- Em 2026-10-06, um `X-Forwarded-For` forjado virava o IP do cliente no Render. A
  ADR-012 desligou os cabeçalhos de proxy no Uvicorn (`--no-proxy-headers`).
- Com isso, o par do socket é o proxy local do Render (`127.0.0.1`), e **todos os
  clientes dividem o mesmo balde por IP**: o de login e o `standard` dos anônimos. A
  ADR-017 já separa os usuários autenticados.

## Decisão

1. **Configuração explícita:** `MARKET_PULSE_TRUSTED_PROXY_HOPS` (0 a 5, padrão 0).
2. **Com 0,** o cabeçalho é ignorado e o par do socket é o cliente. É o comportamento
   atual, que continua no staging.
3. **Com N > 0,** o cliente é a N-ésima entrada do `X-Forwarded-For` contada da direita.
   Cada proxy confiável acrescenta o endereço do seu par, então tudo à esquerda dessa
   posição foi escrito pelo cliente e é ignorado. Prefixos forjados não mudam o
   resultado.
4. **Falha segura:** cabeçalho com menos de N entradas ou valor que não é IP voltam ao
   par do socket. Não há valor inventado.
5. **Um só ponto:** `app/core/client_ip.py` serve o rate limit (middleware) e o
   limitador de login e cadastro.

## Risco de topologia: por que N continua 0

O valor de N só é seguro se **todo** tráfego passar pela mesma cadeia. Hoje há dois
caminhos até a API:

- navegador → Vercel (proxy same-origin, ADR-008) → Render → API;
- cliente → Render → API, direto no domínio `onrender.com`.

Se N for ajustado para o primeiro caminho, quem chamar o Render direto escolhe a
entrada que cai na posição N e forja o endereço. Antes de ativar, é preciso:

1. **Medir** quantas entradas cada caminho entrega à API, registrando só a contagem e
   nunca o IP.
2. **Fechar o caminho direto** ou exigir dele a mesma profundidade. Uma opção é a API
   aceitar só requisições com um segredo que o lado da Vercel injeta, o que exige ADR
   própria e gestão de segredo.

As duas etapas dependem de deploy no staging, que exige autorização do usuário.

## Consequências

- Sem mudança de comportamento até a ativação. O staging continua com um balde único
  por IP para anônimos e para o login, aceitável para um usuário (H-23, classe C).
- Abrir o produto a outras pessoas continua bloqueado por este item.

## Evidência

`apps/api/tests/test_trusted_proxy_hops_day39.py`: cabeçalho ignorado com 0; N-ésima
entrada da direita com 1 e 2 (inclusive em cabeçalhos repetidos); prefixos forjados sem
efeito; cabeçalho curto ou inválido volta ao par; IPv6 aceito; prefixos rotativos não
renovam a cota de login; limites da configuração.
