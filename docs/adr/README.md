# Índice de ADRs

- **Atualizado em:** 2026-10-13 (Dia 41, ADRs 028 e 029).
- **Regra:** uma ADR aceita não é editada em silêncio; mudança material exige ADR nova
  (`AGENTS.md`). Este índice só aponta o estado de implementação e de deploy de cada uma.
- **Staging** = `feature/dia-29-staging` (`1747184`), conferido em 2026-10-11: web e API no
  mesmo commit desde o deploy manual da API (H-28 encerrado). As ADRs 021 em diante estão só
  em `feature/dia-41-sync`.

| ADR | Decisão | Status | Implementação | No staging |
| --- | --- | --- | --- | --- |
| [001](001-modular-monolith.md) | Monólito modular | Accepted | Sim | Sim |
| [002](002-external-cron.md) | Refresh por cron externo | Accepted | Workflow pronto; agendamento desabilitado e Actions bloqueado (H-05) | Não se aplica |
| [003](003-financial-content-boundary.md) | Fronteira de conteúdo financeiro | Accepted | Validador editorial; avisos do §11 no Dia 35 | Sim (avisos na web) |
| [004](004-provider-licensing-matrix.md) | Matriz de licenças, `default deny` | Accepted | 11 providers, todos `UNREVIEWED`; nenhum `PUBLIC_APPROVED` | Sim (só DEMO) |
| [005](005-hybrid-progressive-rendering.md) | Renderização híbrida e progressiva | Accepted | Sim | Sim |
| [006](006-monochrome-financial-chart-semantics.md) | Visual monocromático e semântica dos gráficos | Accepted | Sim; direção com pistas não cromáticas no Dia 36 | Sim (web) |
| [007](007-informational-portfolios-ledger-performance.md) | Carteiras informativas e ledger | Accepted | Sim | Sim |
| [008](008-same-origin-api-proxy.md) | Proxy same-origin no Next.js | Accepted | Sim | Sim |
| [009](009-csrf-before-rate-limit.md) | CSRF antes do rate limit | Accepted | Sim | Não |
| [010](010-portfolio-event-note-erasure.md) | Anulação da nota na anonimização | Accepted | Sim; migration `20261005_0012` | Não |
| [011](011-registration-by-invite.md) | Cadastro por convite | Accepted | **Não implementada**: exige migration e consumo transacional verificados em Postgres | Não (staging usa `CLOSED`) |
| [012](012-untrusted-proxy-headers.md) | Ignorar cabeçalhos de proxy | Accepted | `--no-proxy-headers` | Sim |
| [013](013-history-display-downsampling.md) | Downsampling M4 opt-in | Accepted | Sim | Sim |
| [014](014-chart-engine-keep-svg.md) | Manter o SVG P0 | Accepted | Sim | Sim (sem mudança de código) |
| [015](015-oklch-tokens-and-theme-contrast.md) | Tokens OKLCH e contraste | Accepted | Sim | Sim (web) |
| [016](016-global-persisted-theme.md) | Tema global persistido | Accepted | Sim | Sim (web) |
| [017](017-per-user-rate-limit.md) | Limite por usuário autenticado | Accepted | Sim | Não |
| [018](018-portfolio-overview-and-aligned-downsampling.md) | Overview da carteira e downsampling alinhado | Accepted | Sim | Sim |
| [019](019-global-atlas-table-and-basic-heatmap.md) | Global Atlas tabular e heatmap básico | Accepted | Sim | Sim |
| [020](020-trusted-proxy-hops.md) | IP por saltos de proxy confiáveis | Accepted (mecanismo) | Sim, **desligado** (`MARKET_PULSE_TRUSTED_PROXY_HOPS=0`) até medir a cadeia | Não |
| [021](021-optional-color-vision-palette.md) | Paleta opcional para daltonismo | Accepted | Sim, desligada por padrão; revisão de Cláudio pendente | Não |
| [022](022-day-41-frontend-integration.md) | Integração do Dia 41 | Accepted | Sim, em `feature/dia-41-sync` | Não |
| [023](023-markets-hub-chart-type-and-motion.md) | Hub de mercados, linha/candles e movimento do Atlas | Accepted | Sim, em `feature/dia-41-sync`; movimento desligável por `NEXT_PUBLIC_ATLAS_MOTION=off` | Não |
| [024](024-benchmark-units-pending.md) | Unidade dos benchmarks | **Proposed** | Mitigação: limitação "Unidade não declarada" na API e na tela | Não |
| [025](025-provider-registry-and-lifecycle.md) | Registro, ciclo de vida e camada canônica de providers | Accepted (arquitetura) | Sim, em `feature/dia-41-sync`; nenhum provider ativo | Não |
| [026](026-particle-atlas-visual-system-v2.md) | Sistema visual v2 do Particle Atlas | Accepted | Sim, em `feature/dia-41-sync` | Não |
| [027](027-owner-private-real-data-staging.md) | Dados reais no staging privado, por decisão do responsável | Accepted | Sim, em `feature/dia-41-sync`; ativação por `MARKET_PULSE_REAL_DATA_PROVIDERS` | Não |
| [028](028-visual-identity-v3-chart-workspace.md) | Identidade visual v3 e workspace de gráficos (substitui a parte visual da diretriz Particle Atlas e a ADR-014 no workspace) | Accepted | Sim, em `feature/dia-41-sync` | Não |
| [029](029-owner-real-data-universe.md) | Universo de dados reais do responsável e panorama de mercados | Accepted | Sim, em `feature/dia-41-sync` | Não |

Alternativas que não viraram decisão estão em
[DISCARDED_ALTERNATIVES.md](../engineering/DISCARDED_ALTERNATIVES.md).
