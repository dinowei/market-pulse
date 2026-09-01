# Enterprise Engineering Baseline

Status: obrigatória e canônica para engenharia do Market Pulse.

## Princípio não negociável

Não crie uma solução nova se já existir um padrão documentado no Market Pulse. Amplie o padrão existente ou pare e proponha uma decisão arquitetural.

## Quando ler esta baseline

Leia antes de qualquer tarefa que envolva backend, frontend, banco de dados, API, testes, infraestrutura, segurança, contratos, providers, jobs, autenticação, CI ou integração entre módulos.

## Ordem de leitura

1. Instrução direta da tarefa.
2. `AGENTS.md` da raiz e do subdiretório aplicável.
3. Esta baseline.
4. `docs/PROJECT_SPEC.md`.
5. Política financeira canônica.
6. `docs/ROADMAP_30_DAYS.md` e `docs/ARCHITECTURE.md`.
7. ADRs aceitas e contratos OpenAPI aplicáveis.

## Módulos e dependências

- Organize o backend por módulos de domínio, com limites explícitos e dependências direcionadas.
- Módulos não devem importar detalhes internos de outros módulos; use contratos, serviços ou eventos documentados.
- Providers externos ficam atrás de interfaces substituíveis e não podem dominar o domínio.

## Endpoints e contratos

- Toda API pública usa o prefixo versionado `/api/v1`.
- Rotas devem declarar autenticação, autorização, entrada, saída, códigos HTTP e efeitos colaterais.
- OpenAPI é o contrato; alterações incompatíveis exigem decisão documentada e estratégia de migração.

## Erros Problem Details

- Erros HTTP seguem `application/problem+json`.
- O corpo deve conter `type`, `title`, `status`, `detail` seguro e `instance` quando útil.
- Erros de domínio usam códigos estáveis em `type`; nunca exponha stack trace, segredos, SQL ou detalhes de provider.

## Request ID e observabilidade

- Toda requisição recebe ou propaga `X-Request-ID`.
- O identificador aparece nos logs estruturados e em respostas de erro.
- Logs não podem conter tokens, senhas, cookies, dados financeiros desnecessários ou PII além do mínimo operacional.

## Paginação e ordenação

- Coleções paginadas aceitam `limit`, `offset`, `sort` e `order` apenas em campos allowlisted.
- `limit` padrão é 20 e máximo é 100; valores inválidos produzem erro de contrato.
- A ordenação deve ser determinística, incluindo desempate por identificador quando necessário.

## Idempotência

- Operações de escrita repetíveis devem aceitar `Idempotency-Key` e documentar sua janela de retenção.
- A mesma chave com payload diferente deve falhar de forma segura; a mesma chave com payload igual deve devolver o resultado original.
- Não use idempotência como substituto de transação ou autorização.

## Banco, migrations e integridade

- Alterações de schema são feitas exclusivamente por Alembic, revisáveis e reversíveis quando tecnicamente possível.
- Migrations devem ser pequenas, determinísticas e compatíveis com rollout incremental.
- Integridade referencial, unicidade e imutabilidade de registros financeiros devem ser garantidas no banco e testadas.

## Schema financeiro

- Valores monetários e percentuais usam tipos decimais/numeric apropriados; nunca `FLOAT`, `REAL` ou `DOUBLE PRECISION`.
- Dados financeiros carregam fonte, horário do dado, horário de ingestão e estado `FRESH`, `STALE` ou `UNAVAILABLE`.
- Carteiras são informativas e factuais; não representam recomendação, suitability, gestão ou promessa de retorno.

## Testes

- Mantenha a pirâmide: testes unitários rápidos, integração para banco/Redis e poucos testes de contrato/fluxo.
- Toda regra de segurança, imutabilidade, fallback, freshness e cálculo financeiro deve ter teste determinístico.
- Testes não usam providers financeiros reais, credenciais reais ou serviços externos não autorizados.

## Providers e licenciamento

- O padrão de licenciamento é default deny por provider, plano, endpoint, dataset, finalidade e modalidade de uso.
- DEMO, autenticação administrativa, feature flag e acesso interno não concedem direitos de licença.
- Provider indisponível usa último dado válido somente quando permitido, marcando o estado como `STALE`.

## Frontend e cliente gerado

- O frontend consulta o contrato OpenAPI por meio de `apps/web/src/generated/api.ts`; não duplique schemas nem use `any` para ocultar incompatibilidades.
- UI financeira deve expor fonte, atualização e freshness, sem apresentar conteúdo como recomendação.
- HTML/CSS/SVG acessível é o padrão; Canvas 2D e WebGL exigem justificativa e feature flag conforme as ADRs.

## Feature flags

- Flags devem ter nome, finalidade, valor padrão seguro, responsável e plano de remoção documentados.
- Recursos experimentais permanecem desligados por padrão e não podem contornar autorização, licenciamento ou segurança.

## Documentação e decisões

- Toda mudança arquitetural relevante exige ADR antes ou junto da implementação.
- Documentos canônicos devem apontar para a fonte vigente e registrar lacunas sem reconstruir arquivos ausentes sem autorização.
- Exemplos de configuração usam apenas valores fictícios em `.env.example`.

## Commits

- Use Conventional Commits, com escopo pequeno e mensagem que descreva a mudança efetiva.
- Não misture refatoração não relacionada, código de produto e documentação de governança no mesmo commit.

## Condições de parada

Pare antes de escrever quando houver conflito entre fontes canônicas, requisito sem decisão, licença incerta, risco de segredo, alteração incompatível sem migração ou necessidade de tocar arquivo fora do escopo autorizado.

## Checklist de entrega

- [ ] Fontes canônicas e AGENTS aplicáveis foram lidos.
- [ ] Escopo e impacto foram confirmados.
- [ ] Contratos, segurança, licenciamento e freshness foram preservados.
- [ ] Testes e verificações proporcionais foram executados.
- [ ] `git diff --check` passou e somente arquivos autorizados mudaram.
- [ ] Não há segredos, provider real, deploy, push ou login externo.
