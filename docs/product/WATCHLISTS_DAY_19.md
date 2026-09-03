# Watchlists e favoritos privados — Dia 19

O Dia 19 adiciona acompanhamento privado de instrumentos ao Market Pulse. Uma
watchlist guarda apenas a identidade do instrumento e a ordem escolhida pelo
usuário; preços, cotações e histórico continuam vindo dos contratos públicos de
market data, com provenance e estados próprios.

## Contrato da API

Todos os endpoints exigem a sessão opaca do Dia 18 e filtram por `user_id` no
backend:

- `GET/POST /api/v1/watchlists` lista e cria listas;
- `GET/PATCH/DELETE /api/v1/watchlists/{watchlist_id}` consulta, renomeia e
  remove uma lista própria;
- `POST/DELETE /api/v1/watchlists/{watchlist_id}/items/{canonical_id}` adiciona
  ou remove um instrumento;
- `PATCH /api/v1/watchlists/{watchlist_id}/items/reorder` persiste a ordem
  completa por `canonical_id`;
- `POST/DELETE /api/v1/watchlists/favorites/{canonical_id}` cria/reutiliza a
  lista de sistema `Favoritos` por usuário.

IDs de outra pessoa retornam `404`, evitando enumeração. Ausência de sessão
retorna `401` em Problem Details. Unicidade e repetição de inclusão são tratadas
sem duplicar itens nem produzir erro 500.

## Universo e dados

O instrumento é validado pelo `canonical_id` do catálogo mestre. O MVP permite
entradas P0 operacionais e P0 de catálogo; fundos tradicionais, identidades fora
de escopo, `FUTURE_REVIEW` e dados indisponíveis permanecem bloqueados com
`BLOCKED_SCOPE`. A watchlist não persiste preço, volume, variação ou histórico.

Cada item expõe símbolo/alias, nome, tipo, bolsa, moeda, timezone,
`canonical_id` e estado de suporte. Sem fonte aprovada, qualquer preço é
apresentado como indisponível; o Dia 19 não ativa provider nem dataset real.

## Interface e segurança

A rota `/watchlists` integra o visual Particle Atlas e mantém tema escuro/claro,
tipos do cliente OpenAPI gerado, cookie `HttpOnly` e nenhum token em
`localStorage`, `sessionStorage` ou JavaScript. O estado sem sessão oferece
login; loading, vazio e erro são explícitos. Reordenação usa botões acessíveis
de subir/descer, além de remoção e exclusão de listas não sistêmicas. Monogramas,
tickers e metadados substituem logos sem licença.

Watchlists são informativas e não constituem recomendação, sinal, timing,
alocação, gestão de carteira ou promessa de retorno.

## Pendências conscientes

- Não há carteiras, P&L, TWR ou performance neste dia.
- Não há provider financeiro real, scraping, `PUBLIC_APPROVED`, logos licenciados,
  compartilhamento de listas ou integração com corretora.
- A persistência usa a migration incremental `20260903_0006`, adicionando
  `is_system`, `position` e índices sem alterar migrations anteriores.
