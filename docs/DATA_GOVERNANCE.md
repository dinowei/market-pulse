# Governança de dados

- **Status:** Accepted
- **Data:** 2026-08-30

## Princípios

- PostgreSQL é a fonte persistente; Redis é cache/lock.
- Dado só é persistido após validação.
- Payload nativo permanece no adapter; logs não armazenam credenciais nem resposta sensível.
- Timestamps são UTC na persistência e exibidos com zona explícita.
- Fonte, timestamp da fonte, coleta, licença, `DataLevel` e `Freshness` acompanham o dado.

## Qualidade

Valores passam por validação de símbolo, bolsa, moeda, tipo numérico, faixa plausível e coerência temporal. Falha não sobrescreve snapshot válido. Fallback é por ativo e sempre explícito como `STALE`; sem snapshot validado, o estado é `UNAVAILABLE`.

## Níveis

- `REAL_TIME`: somente com semântica/licença confirmadas.
- `DELAYED`: atraso conhecido e visível.
- `EOD`: fechamento, não intraday.
- `DEMO`: sintético/determinístico e inequivocamente rotulado.

`DataLevel` é independente de `Freshness`, cujos valores são `FRESH`, `STALE` e `UNAVAILABLE`.

## Licença e exposição

Somente uma combinação exata com status operacional `PUBLIC_APPROVED` e classe de licença compatível, como definido na [matriz canônica](DATA_PROVIDER_LICENSE_MATRIX.md), pode ser exposta ao usuário comum. Demais estados são bloqueados pelo domínio. Gratuidade, `DEMO`, autenticação administrativa e feature flag não implicam redistribuição ou direito de uso.

## Carteiras informativas

Carteiras próprias são registros factuais e informativos do usuário. O ledger aceita eventos manuais de compra, venda, aporte, retirada, taxa e provento quando os campos forem válidos; esses registros não são ordem, gestão, recomendação ou suitability. Cálculos de posição, custo, patrimônio, P&L e performance devem ser reproduzíveis, preservar moeda-base, metodologia, timestamps e limitações, e marcar `PARTIAL`/`UNAVAILABLE` quando faltar preço ou FX aprovado.

## Retenção e privacidade

Retenção de snapshots, sessions e ingestion runs será definida antes da produção. Minimizar dados pessoais; não colocar e-mail, tokens ou cookies em logs. Pedidos de remoção exigem processo autenticado futuro.

**Adendo de 2026-10-07 (Dia 40).** Parte do que estava como futuro foi implementada no
Dia 28; o estado atual está no [checklist de compliance](COMPLIANCE_CHECKLIST.md), §3:

- expurgo com retenção padrão de 90 dias para quarentenas, payloads brutos e telemetria
  (`app/retention.py`), sem tocar em `audit_logs`; ainda sem execução agendada;
- exclusão de conta por anonimização, com auditoria, e exportação dos dados do usuário
  autenticado;
- sessões no Redis com expiração.

Continuam em aberto o aviso de privacidade e os termos de uso para o usuário.
