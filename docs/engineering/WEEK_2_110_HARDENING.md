# Dia 14.1 — hardening 110% da Semana 2

Esta etapa responde à auditoria que classificou a Semana 2 como `PARCIAL`.
O objetivo foi blindar catálogo, contratos, providers, cache, calendário,
Default Deny e contratos de gráficos antes da Semana 3. Nenhum provider real,
dado externo, segredo real ou tela visual foi ativado.

## Correções aplicadas

- Busca HTTP agora usa o catálogo estático, pesquisa símbolo, nome, alias e
  `canonical_id`, e informa `P0_OPERATIONAL`, `CANDIDATE_FUTURE`,
  `UNSUPPORTED` ou `BLOCKED_SCOPE`.
- `MUTUAL_FUND` permanece bloqueado até existir cobertura licenciada aprovada;
  ticker continua sendo alias e `canonical_id` é a identidade.
- Contratos de quote/série/cache carregam dataset, timestamps, latência,
  limitações e estado de indisponibilidade; séries suportam `PRICE`,
  `INDEX_100`, fallback tabular e reduced motion sem suavização artificial.
- `ProviderResult` rejeita floats financeiros e adapters exigem um
  `ProviderResult` normalizado; payload bruto não atravessa a fronteira.
- Rotas e cache permanecem fail-closed quando não há dataset aprovado.
- Calendário aceita timezone IANA e feriados configuráveis (incluindo fixtures
  B3 e EUA); sem calendário explícito, a semântica histórica de freshness é
  preservada para compatibilidade.
- O gate de supply chain verifica ausência de `yfinance` em manifestos, lock e
  imports, e o secret scan reconhece chaves dos providers candidatos sem
  aceitar valores reais em `.env.example`.

## Limitações conscientes

As rotas de quotes, séries, carteiras, performance e Morning Call continuam
sem persistência de produto; retornam estados vazios/controlados até os dias
correspondentes. O catálogo de feriados ainda é fornecido por configuração,
não é um calendário mundial persistido. Campos históricos anuláveis no banco
foram preservados para compatibilidade; contratos de serviço rejeitam respostas
operacionais sem provenance mínima. `ProviderResult` continua genérico para
metadados, mas rejeita floats recursivamente.

## Regressão e consumo pela Semana 3

`apps/api/tests/test_day14_1_hardening.py` cobre busca, identidade, colisões,
fundos bloqueados, provenance/latência, adapter boundary, Default Deny,
calendário, feriados e contratos de série. A Semana 3 pode consumir apenas
identidades canônicas e contratos que exibam fonte, dataset, timestamps,
`DataLevel`, `Freshness`, limitações e estados `PARTIAL`/`UNAVAILABLE`.
Nenhum frontend deve inferir cotação real do catálogo, preencher gaps,
suavizar séries ou tratar `DEMO` como licença.
