# ADR-022: Integração do Dia 41 (página de ativo, conta, proventos, drawdown e auditoria)

- Status: Accepted
- Data: 2026-10-11
- Decisores: responsável humano pelo produto (autorizou as tarefas T1 a T8 do relatório de
  sincronização com o NotebookLM em 2026-10-11); implementação por Claude Code
- Relação: [ADR-005](005-hybrid-progressive-rendering.md),
  [ADR-007](007-informational-portfolios-ledger-performance.md),
  [ADR-018](018-portfolio-overview-and-aligned-downsampling.md) e
  [ADR-019](019-global-atlas-table-and-basic-heatmap.md)

## Contexto

O relatório de sincronização mostrou que o backend estava à frente da interface: favoritos,
exportação e exclusão de conta e o lote da comparação existiam sem tela. A página de ativo
(P0 na especificação e no Dia 17 do roadmap v2) não existia como rota. O NotebookLM pedia
ainda drawdown, proventos por ativo, filtros por classe e auditoria das tentativas
editoriais negadas.

## Decisões

1. **Páginas estáticas, consulta na URL.** `/assets?id=`, `/compare?ids=` e
   `/portfolios?canonical_id=` continuam pré-renderizadas (ADR-005). O parâmetro é lido no
   cliente, dentro de um `Suspense`, e validado pelo formato do `canonical_id`. Rotas
   dinâmicas tirariam as páginas do gate de bundle e trocariam HTML estático por função
   no servidor.
2. **Página de ativo** reaproveita os componentes do dashboard (período, modo, gráfico,
   tabela, proveniência, selo) e só oferece ações com endpoint: favoritar, adicionar à
   watchlist, registrar evento na carteira (formulário pré-preenchido) e comparar com o
   Ibovespa. Instrumento fora do catálogo mostra "Ativo não encontrado".
3. **Proventos por ativo:** `GET /api/v1/market-data/corporate-actions/{canonical_id}`.
   Fora do DEMO local, `UNAVAILABLE` com `DATASET_NOT_APPROVED`. No DEMO, passa pelo mesmo
   `LicenseService` das cotações, restrito ao dataset sintético de eventos; uma linha
   bloqueada torna toda a resposta `UNAVAILABLE`, para nunca mostrar uma lista parcial como
   completa.
4. **Drawdown da carteira:** queda em relação ao maior patrimônio anterior, só sobre curva
   sem fluxos externos depois do primeiro dia, a mesma condição do TWR. A condição virou um
   verificador único usado pelos dois cálculos. Fora dela, `UNAVAILABLE` com o motivo. O
   drawdown entra no `/overview` (uma requisição, ADR-018) e tem rota própria.
5. **Comparação:** até 10 séries (limite do contrato do lote), escolhidas pela busca do
   catálogo e pelos benchmarks que a API publica.
6. **Classes de ativo:** filtros a partir do `instrument_type` que a API devolve. Fundos e
   Renda fixa aparecem como indisponíveis, com o motivo, e nunca como filtro funcional.
7. **Conta:** `/account` com exportação dos dados e exclusão. A exclusão exige digitar
   `EXCLUIR` e confirmar que é irreversível, e descreve o que acontece. O vermelho não é
   usado no botão, porque significa `DOWN`.
8. **Auditoria de negação editorial:** toda recusa de papel editorial grava uma linha em
   `audit_logs` (`editorial_permission_denied`, resultado `DENIED`) com papel, método e rota;
   nunca o conteúdo enviado nem dados do usuário. Uma falha na gravação não troca o 403 por
   500.

## Consequências

- O contrato ganhou `InstrumentCorporateActionsResponse`, `PortfolioDrawdownResponse` e o
  campo `drawdown` no `/overview` (aditivo). OpenAPI e cliente gerado foram atualizados.
- A primeira carga de JS de `/assets`, `/compare` e `/portfolios` ficou entre 184 e 186 KB
  gzip, dentro do orçamento de 200 KB.
- D-1 e D-3 do fluxo editorial (H-25) continuam pendentes; esta ADR só acrescenta a trilha
  das recusas.

## Evidência

- Backend: `test_asset_events_day41.py`, `test_portfolio_drawdown_day41.py`,
  `test_editorial_denial_audit_day41.py` e o teste do `/overview` com o drawdown.
- Frontend: `day41-frontend.test.ts`.
- Gate WCAG com `/assets?id=` e `/account`: 33 de 33, local.
