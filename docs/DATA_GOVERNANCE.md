# Governança de dados

- **Status:** Accepted
- **Data:** 2026-08-30

## Princípios

- PostgreSQL é a fonte persistente; Redis é cache/lock.
- Dado só é persistido após validação.
- Payload nativo permanece no adapter; logs não armazenam credenciais nem resposta sensível.
- Timestamps são UTC na persistência e exibidos com zona explícita.
- Fonte, timestamp da fonte, coleta, licença, `data_level` e freshness acompanham o dado.

## Qualidade

Valores passam por validação de símbolo, bolsa, moeda, tipo numérico, faixa plausível e coerência temporal. Falha não sobrescreve snapshot válido. Fallback é por ativo e sempre explícito como stale.

## Níveis

- `REAL_TIME`: somente com semântica/licença confirmadas.
- `DELAYED`: atraso conhecido e visível.
- `EOD`: fechamento, não intraday.
- `DEMO`: sintético/determinístico e inequivocamente rotulado.

## Licença e exposição

Somente `PUBLIC_COMMERCIAL` pode ser exposto ao usuário comum. Demais classes são bloqueadas por serviço de domínio. Gratuidade não implica redistribuição.

## Retenção e privacidade

Retenção de snapshots, sessions e ingestion runs será definida antes da produção. Minimizar dados pessoais; não colocar e-mail, tokens ou cookies em logs. Pedidos de remoção exigem processo autenticado futuro.
