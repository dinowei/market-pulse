# Refresh interno — Dia 12.1

O refresh do Dia 12.1 é um serviço interno de coordenação, não uma rota
pública. Ele recebe `dataset`, `canonical_id` e `capability`, gera uma
identidade determinística de job e valida o acesso pelo Default Deny antes de
qualquer adapter.

## Fluxo e estados

1. Validar provider, plano, endpoint, dataset, finalidade, modalidade,
   ambiente, evidência, status e nível de dado.
2. Retornar `SKIPPED_LICENSE_BLOCKED` sem chamar provider quando a decisão for
   negada.
3. Adquirir lock distribuído com owner e TTL; concorrência retorna
   `SKIPPED_LOCKED`.
4. Registrar a tentativa em `ingestion_runs` quando persistência estiver
   conectada e chamar somente adapter configurado e autorizado. Sem provider
   aprovado, o fluxo DEMO pode usar exclusivamente o `DemoProvider` sintético.
5. Sanitizar payload, normalizar, persistir de forma idempotente e enviar
   conflitos para quarentena.
6. Invalidar somente a chave de cache do instrumento/dataset afetado e liberar
   o lock pelo owner.

Estados possíveis: `SUCCESS`, `PARTIAL`, `SKIPPED_LICENSE_BLOCKED`,
`SKIPPED_LOCKED`, `FAILED` e `UNAVAILABLE`. O serviço atual implementa a
coordenação determinística e a invalidação granular; a rota pública e a escrita
completa de ingestão permanecem escopo do Dia 13.

Nenhum provider real, segredo, scraping ou dado financeiro real é ativado por
este módulo. Dados DEMO permanecem explicitamente DEMO e nunca recebem direitos
de licença por esse rótulo.
