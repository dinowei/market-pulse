# Objetivos iniciais de serviço

- **Status:** Proposed; objetivos do beta, não SLA contratual
- **Data:** 2026-08-30

| Indicador | Objetivo inicial | Evidência planejada |
| --- | --- | --- |
| API de leitura disponível | 99% durante janela de demonstração | health e logs |
| Resposta cacheada p95 | até 500 ms em ambiente beta | métrica HTTP |
| Resposta sem cache p95 | até 3 s, excluindo timeout externo | métrica HTTP/provider |
| Identificação de stale | 100% das respostas fallback | contract/integration tests |
| Proveniência | 100% dos itens financeiros | schema/contract tests |
| Refresh idempotente | nenhuma duplicação para mesma chave | integration tests |
| Conteúdo publicado validado | 100% com revisão humana | audit trail |

Freshness por classe de ativo, duração máxima de stale e janelas de mercado são pendências. Alertas e orçamento de erro serão definidos após a primeira integração real. Não existe compromisso público de tempo real no Dia 1.
