# Gate da Semana 3

## Estado

O gate reúne o frontend P0, autenticação, watchlists, carteiras e a camada de
performance factual do Dia 21. O caminho permanece local e demonstrativo; não
há provider financeiro real nem dataset `PUBLIC_APPROVED` ativo.

## Evidências esperadas

- API versionada com sessões opacas, isolamento horizontal e Problem Details.
- Watchlists e carteiras privadas por usuário.
- Ledger append-only com replay `Decimal`, valuation, P&L e estados parciais.
- TWR auditável e indisponível quando faltam séries históricas aprovadas.
- Frontend com cliente TypeScript gerado, provenance, estados e fallback tabular.
- Testes, lint, typecheck, build, migration e health checks reproduzíveis.

## Limitações conscientes

Fixtures `DEMO/STALE` servem apenas para demonstração local. Sem preço ou FX
aprovado, nenhum total é estimado. Performance factual não é recomendação e não
autoriza contratação de provider, cobrança, integração com corretora ou deploy.
