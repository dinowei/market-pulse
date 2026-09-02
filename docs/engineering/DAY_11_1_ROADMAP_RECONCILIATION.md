# Dia 11.1 — Reconciliação do roadmap com a execução

Em 2026-09-02, o roadmap foi alinhado à execução aprovada do Dia 11. A instrução direta do usuário prevaleceu sobre a descrição anterior do roadmap: o Dia 11 foi executado como pipeline de eventos corporativos para dividendos, JCP, splits, grupamentos e reconciliação auditável.

O código correspondente foi validado e está registrado nos commits `04ea5be` e `4c71c6f`. Esta alteração é exclusivamente documental; não expande o escopo de produto aprovado, não altera código, migrations, testes ou contratos públicos.

A tarefa de refresh idempotente e `ingestion_runs` não foi apagada nem perdida. Ela foi realocada explicitamente para o Dia 12.1, mantendo lock, auditoria e autenticação interna como critérios próprios.
