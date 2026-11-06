# ADR-012: Não confiar em cabeçalhos de proxy para o IP do cliente (mitigação do H-23)

- Status: Accepted
- Data: 2026-10-06
- Decisores: responsável técnico (Claude Code), com delegação explícita do operador do
  projeto; correção de segurança num ambiente já implantado
- Relação: mitigação provisória do H-23 ([DAY29_HANDOFF.md](../DAY29_HANDOFF.md)); a
  solução definitiva segue agendada para o Dia 39. Complementa a ADR-008.

## Contexto

O rate limit e o limitador de autenticação identificam o cliente por
`request.client.host`. No staging do Render, o Uvicorn reescreve esse valor a partir de
`X-Forwarded-For`, e o proxy do Render **não filtra** um `X-Forwarded-For` enviado pelo
próprio cliente.

**Medido em 2026-10-06:**

- No staging, uma requisição com `X-Forwarded-For: 203.0.113.77` apareceu no log de acesso
  como vinda de `203.0.113.77:0`.
- Localmente, com `FORWARDED_ALLOW_IPS='*'`, o Uvicorn faz o mesmo. Com
  `--no-proxy-headers`, registra o par real da conexão.

**Impacto:** trocando o cabeçalho a cada tentativa, um atacante escapava de todo limite
por IP, inclusive do limite de login (5/60 s). Isso abre caminho para força bruta online
contra contas existentes.

## Decisão

Iniciar o Uvicorn com `--no-proxy-headers` no Render (`render.yaml`). O IP usado pelo rate
limit passa a ser o do par da conexão, ou seja, o balanceador interno do Render, que o
cliente não controla.

## Alternativas consideradas

- **Ler o IP de `X-Forwarded-For` pela posição a partir da direita (saltos confiáveis):**
  correto se a cadeia de proxies for estável, mas a estrutura do cabeçalho no Render não
  foi verificada em fonte oficial. Fica para o Dia 39, com medição.
- **`CF-Connecting-IP` ou `True-Client-IP`:** só há afirmação em fórum, não em
  documentação oficial do Render, de que esses cabeçalhos chegam sem interferência do
  cliente. Exige verificação antes de adotar.

## Consequências

- **Positiva:** o IP do rate limit deixa de ser forjável.
- **Negativa:** clientes distintos passam a compartilhar baldes por IP do balanceador. Um
  terceiro pode esgotar o balde de login e bloquear o acesso por 60 s (negação de serviço
  leve), mas não consegue força bruta. Aceitável num staging privado de um único usuário;
  **inaceitável para abrir o produto**, por isso o H-23 continua obrigatório no Dia 39.
- O esquema da requisição vista pela aplicação passa a ser o da conexão interna. A API
  não usa o esquema para cookies (o `Secure` vem da configuração).

## Como revisar esta decisão

No Dia 39: medir a estrutura real de `X-Forwarded-For` no Render, escolher a extração por
saltos confiáveis ou um cabeçalho verificado, e cobrir com testes de forja.
