# Índice de ADRs

- **Atualizado em:** 2026-10-07 (Dia 40).
- **Regra:** uma ADR aceita não é editada em silêncio; mudança material exige ADR nova
  (`AGENTS.md`). Este índice só aponta o estado de implementação e de deploy de cada uma.
- **Staging** = `feature/dia-29-staging`, no ar com o commit `60df9ca`. As ADRs 009 em
  diante estão em `feature/dia-30-rc` ou `feature/dia-31-34`, **sem deploy**.

| ADR | Decisão | Status | Implementação | No staging |
| --- | --- | --- | --- | --- |
| [001](001-modular-monolith.md) | Monólito modular | Accepted | Sim | Sim |
| [002](002-external-cron.md) | Refresh por cron externo | Accepted | Workflow pronto; agendamento desabilitado e Actions bloqueado (H-05) | Não se aplica |
| [003](003-financial-content-boundary.md) | Fronteira de conteúdo financeiro | Accepted | Validador editorial; avisos do §11 no Dia 35 | Parcial: os avisos do Dia 35 não |
| [004](004-provider-licensing-matrix.md) | Matriz de licenças, `default deny` | Accepted | 11 providers, todos `UNREVIEWED`; nenhum `PUBLIC_APPROVED` | Sim (só DEMO) |
| [005](005-hybrid-progressive-rendering.md) | Renderização híbrida e progressiva | Accepted | Sim | Sim |
| [006](006-monochrome-financial-chart-semantics.md) | Visual monocromático e semântica dos gráficos | Accepted | Sim; direção com pistas não cromáticas no Dia 36 | Parcial |
| [007](007-informational-portfolios-ledger-performance.md) | Carteiras informativas e ledger | Accepted | Sim | Sim |
| [008](008-same-origin-api-proxy.md) | Proxy same-origin no Next.js | Accepted | Sim | Sim |
| [009](009-csrf-before-rate-limit.md) | CSRF antes do rate limit | Accepted | Sim | Não |
| [010](010-portfolio-event-note-erasure.md) | Anulação da nota na anonimização | Accepted | Sim; migration `20261005_0012` | Não |
| [011](011-registration-by-invite.md) | Cadastro por convite | Accepted | **Não implementada**: exige migration e consumo transacional verificados em Postgres | Não (staging usa `CLOSED`) |
| [012](012-untrusted-proxy-headers.md) | Ignorar cabeçalhos de proxy | Accepted | `--no-proxy-headers` | Sim |
| [013](013-history-display-downsampling.md) | Downsampling M4 opt-in | Accepted | Sim | Não |
| [014](014-chart-engine-keep-svg.md) | Manter o SVG P0 | Accepted | Sim | Sim (sem mudança de código) |
| [015](015-oklch-tokens-and-theme-contrast.md) | Tokens OKLCH e contraste | Accepted | Sim | Não |
| [016](016-global-persisted-theme.md) | Tema global persistido | Accepted | Sim | Não |
| [017](017-per-user-rate-limit.md) | Limite por usuário autenticado | Accepted | Sim | Não |
| [018](018-portfolio-overview-and-aligned-downsampling.md) | Overview da carteira e downsampling alinhado | Accepted | Sim | Não |
| [019](019-global-atlas-table-and-basic-heatmap.md) | Global Atlas tabular e heatmap básico | Accepted | Sim | Não |
| [020](020-trusted-proxy-hops.md) | IP por saltos de proxy confiáveis | Accepted (mecanismo) | Sim, **desligado** (`MARKET_PULSE_TRUSTED_PROXY_HOPS=0`) até medir a cadeia | Não |

Alternativas que não viraram decisão estão em
[DISCARDED_ALTERNATIVES.md](../engineering/DISCARDED_ALTERNATIVES.md).
