# Runbook de Operações de Produção — Dia 28 (Enterprise Hardening)

Este runbook define os procedimentos operacionais padrão para o Market Pulse em ambientes de produção e staging, cobrindo inicialização segura, rotação de segredos, rotina de backup/restore e estratégia de rollback/resposta a incidentes.

---

## 1. Boot Seguro e Validação de Ambiente

### 1.1 Princípio de Fail-Closed no Startup
Em ambientes de produção (`MARKET_PULSE_ENVIRONMENT=production`) ou staging (`MARKET_PULSE_ENVIRONMENT=staging`), a API executa validação estrita das configurações antes de aceitar qualquer tráfego HTTP (`validate_production_settings` em `app/core/config.py`).

O boot é abortado imediatamente (`ProductionConfigurationError`) nas seguintes condições:
- `MARKET_PULSE_DEMO_ENABLED` configurado como `true` (modo demo é estritamente proibido em produção).
- `MARKET_PULSE_DATABASE_URL` ausente, malformado ou contendo credenciais padrão de desenvolvimento (`market_pulse_local_only`).
- `MARKET_PULSE_REDIS_URL` ausente, malformado ou inacessível.
- `MARKET_PULSE_INTERNAL_REFRESH_SECRET` ausente ou com entropia inferior a 16 caracteres.
- `MARKET_PULSE_CORS_ORIGINS` vazio, contendo wildcard (`*`) com credenciais, ou apontando para `localhost`/`127.0.0.1`.

### 1.2 Política de Origin/CSRF e rotas isentas

`CSRFMiddleware` valida `Origin` (ou, na ausência dele, `Referer`) contra `MARKET_PULSE_CORS_ORIGINS` em **toda** requisição de método mutante (`POST`/`PUT`/`PATCH`/`DELETE`), independentemente de existir cookie de sessão. O comportamento é idêntico em DEMO e em produção.

- **Origin presente e fora da allowlist** → `403` com Problem Details, antes de qualquer validação de corpo ou lógica de negócio. Isso cobre rotas anônimas como `/api/v1/auth/login` e `/api/v1/auth/register`.
- **Nem `Origin` nem `Referer`, e requisição com cookie de sessão** → `403`. Navegador autenticado sempre envia `Origin` em requisição mutante cross-site; a ausência indica requisição forjada.
- **Nem `Origin` nem `Referer`, e requisição sem cookie de sessão** → permitida. É cliente não-navegador (CLI, serviço) sem credencial ambiente para ser abusada, portanto não é vetor de CSRF. Recusar quebraria integrações legítimas servidor-a-servidor.

**Rotas isentas** (`SECRET_AUTHENTICATED_PATHS` em `app/middleware.py`): rotas autenticadas por segredo próprio que o navegador nunca possui. Hoje apenas `POST /api/v1/internal/refresh-quotes`, autenticada por `X-Cron-Secret` com `secrets.compare_digest`. O chamador é o agendador, não tem `Origin` de navegador, e uma requisição forjada cross-site não consegue fornecer o segredo — a allowlist de origem não adicionaria proteção e apenas quebraria o job. **Nunca** inclua nessa lista rota autenticada por cookie.

Histórico: até o Dia 27 essa proteção existia como `demo_origin_guard`, middleware inline em `main.py` ativo somente quando `demo_enabled`. A reescrita do Dia 28 o substituiu por `CSRFMiddleware`, que inicialmente só checava `Origin` quando havia cookie de sessão — deixando login/registro sem checagem de origem. A unificação acima corrige essa regressão e elimina a divergência entre DEMO e produção. Cobertura: `test_csrf_rejects_disallowed_origin_without_session_cookie` e `test_secret_authenticated_cron_route_is_exempt_from_origin_check`.

### 1.3 Verificação de Saúde (Liveness e Readiness)
- `GET /health/live`: Retorna status HTTP 200 se o processo ASGI está ativo e executando loop de eventos.
- `GET /health/ready`: Valida conectividade de rede com PostgreSQL e Redis com timeout restrito (2s banco, 1s cache). Retorna 200 OK se ambos estiverem saudáveis ou 503 Service Unavailable se qualquer dependência falhar.
- `GET /health`: Diagnóstico geral não sensível contendo versão da API e timestamp UTC.

---

## 2. Rotação de Segredos

### 2.1 Segredos Operacionais
1. **Credenciais do Banco de Dados (`MARKET_PULSE_DATABASE_URL`)**:
   - Provisionar usuário/senha secundários no PostgreSQL.
   - Atualizar a variável de ambiente no orquestrador/secrets manager.
   - Realizar rolling restart das instâncias da API.
   - Revogar credenciais antigas após confirmação de que todas as conexões usam a nova senha.

2. **Segredo de Refresh Interno (`MARKET_PULSE_INTERNAL_REFRESH_SECRET`)**:
   - Gerar novo segredo criptográfico: `openssl rand -hex 32`.
   - Atualizar no agendador de tarefas / cron runner e nas instâncias da API simultaneamente.
   - A validação de endpoints protegidos utiliza `secrets.compare_digest` para prevenir ataques de temporização (timing attacks).

3. **Sessões e Cookies (`MARKET_PULSE_AUTH_COOKIE_NAME`, `MARKET_PULSE_AUTH_COOKIE_SECURE`)**:
   - Em produção, `auth_cookie_secure` é automaticamente ativado (`Secure=True`, `HttpOnly=True`, `SameSite=Lax`).
   - Sessões ativas são armazenadas no Redis com TTL (`MARKET_PULSE_AUTH_SESSION_TTL_SECONDS=604800`, 7 dias) e tokens gerados via `secrets.token_urlsafe(48)`.
   - Para invalidação global de emergência (ex: comprometimento de sessão), realizar flush na chave de namespace `auth:session:*` no Redis.

---

## 3. Rotina de Backup e Restore

### 3.1 Procedimento de Backup (`scripts/backup.py`)
O utilitário oficial realiza o backup periódico do PostgreSQL e o snapshot do Redis:

```bash
python scripts/backup.py --output-dir /var/backups/market-pulse --environment production
```

- **PostgreSQL**: Executa `pg_dump` no formato custom comprimido (`-F c`), ou fallback para dump lógico JSON se utilitário de sistema não estiver presente.
- **Redis**: Dispara snapshot assíncrono via comando `BGSAVE` e registra metadados de persistência.
- **Manifesto Assinado**: Cria `backup_manifest.json` com hashes SHA-256 e tamanhos em bytes para verificação de integridade pós-transferência.
- **Segurança**: Todas as URLs registradas têm senhas mascaradas (`***`).

### 3.2 Procedimento de Restore e Validação (`scripts/restore.py`)
O processo de restauração exige verificação obrigatória de manifesto e flag explícita `--confirm`:

```bash
# Pré-requisito do carregador lógico: o dump JSON contém apenas dados, não DDL.
uv run --directory apps/api alembic upgrade head   # contra o banco de destino

# A conexão de destino vem do ambiente/secrets manager, nunca escrita na linha de
# comando: isso evita credencial no histórico do shell e na lista de processos.
export TARGET_DB_URL=...   # conexão do banco de destino

python scripts/restore.py \
  --backup-dir /var/backups/market-pulse/20260927_100000 \
  --target-db-url "$TARGET_DB_URL" \
  --confirm
```

Passos executados:
1. Validação do manifesto `backup_manifest.json` e conferência do SHA-256 do dump contra o valor registrado no backup. Divergência aborta o restore antes de qualquer escrita.
2. Restauração via `pg_restore --clean --if-exists` quando o utilitário está presente e o artefato é `.dump`; caso contrário, carregador lógico transacional.
3. Auditoria pós-restore: contagem de linhas em todas as tabelas `public` da base, para comparação com a origem.

#### 3.2.1 Restrições conhecidas do carregador lógico
- **Schema obrigatório no destino**: o dump lógico carrega linhas, não DDL. Se alguma tabela estiver ausente, o script aborta nomeando as tabelas faltantes e instruindo `alembic upgrade head`. Isso é o caminho normal de DR: schema por migrations, dados por backup.
- **Ordem por dependência de chave estrangeira**: as tabelas são carregadas na ordem topológica derivada de `pg_constraint` (pais antes de filhos). O `TRUNCATE` é emitido uma única vez para todas as tabelas envolvidas, porque truncar tabela por tabela com `CASCADE` apagaria linhas já carregadas.
- **Autorização do destino**: o script restaura para o `--target-db-url` informado e não julga quais bancos são destinos legítimos. A autorização do destino é responsabilidade do operador, conforme este runbook.

#### 3.2.2 Ensaio executado (evidência)
Ensaio real em ambiente local, com Docker Compose ativo, executado no fechamento do Dia 28:
- Backup de `market_pulse_demo` (fallback lógico, pois `pg_dump` não estava no PATH) com manifesto e SHA-256 `77a57e435da11648...`.
- Destino descartável dedicado `market_pulse_restore_test`, migrado com `alembic upgrade head`.
- Restore com `--confirm`, integridade do dump verificada contra o manifesto.
- Paridade verificada: **33 tabelas, 3549 linhas na origem e 3549 no destino, zero divergências**.

---

## 4. Estratégia de Rollback e Resposta a Incidentes

### 4.1 Decisão Arquitetural: Forward-Only vs. Rollback Reversível
- **Migrações de Schema**: O Market Pulse adota **migrações reversíveis com compatibilidade retroativa (Expand & Contract)** como padrão obrigatório.
- **Justificativa**: Em sistemas financeiros com registros contábeis append-only (`portfolio_events`, `audit_logs`), rollbacks destrutivos (`alembic downgrade`) podem causar perda irreparável de histórico contábil registrado durante a janela operacional do deploy.
- **Procedimento para Migrações**:
  1. *Fase de Expansão*: Adicionar novas colunas/tabelas como opcionais (`NULL`) ou com defaults seguros, sem remover colunas depreciadas.
  2. *Deploy da Aplicação*: Subir versão de código compatível com schemas novo e antigo.
  3. *Fase de Contração*: Após período de estabilização, aplicar migration subsequente que limpa colunas depreciadas.
  4. O teste de regressão de migrações populadas (`test_corporate_actions_migration_regression.py`) valida continuamente a reversibilidade de esquemas em ambiente com dados pré-existentes.

### 4.2 Decisão Arquitetural: Exclusão de Conta — Anonimização vs. Hard Delete

`DELETE /api/v1/account` **anonimiza e desativa** o registro do usuário; não executa exclusão física da linha e não é um soft-delete (o dado pessoal deixa de existir, a linha permanece só como âncora de integridade).

**Decisão (2026-10-01, decidida pelo usuário):** exclusão de conta = anonimização + desativação, não soft-delete. Ledger preservado; carteiras arquivadas e com nome neutralizado.

Decisões complementares da mesma data, também do usuário:

| Ref. | Decisão |
| --- | --- |
| D1 | `portfolios.name` é neutralizado para `Carteira removida <id>`; id, `user_id`, `base_currency` e datas permanecem. |
| D2 | O arquivamento (`archived_at`) é mantido. |
| D3 | `portfolio_events.note` fica como **risco residual documentado** (opção A). A ADR da opção B é **obrigatória antes de qualquer abertura do produto a outros usuários**. |
| D4 | O pseudônimo permanece `deleted-<user_id>@market-pulse.invalid`. O sufixo `.invalid` é reservado pela RFC 2606 e nunca recebe e-mail. |
| D5 | O export serializa valores monetários e quantidades como strings decimais e inclui as notas do próprio usuário. |

**Justificativa:** `portfolio_events` é um ledger financeiro append-only protegido por trigger de banco (`prevent_immutable_portfolio_event_change`), e `audit_logs` é registro de auditoria. `portfolio_events.created_by` referencia `users.id`. Um hard delete exigiria apagar ou reescrever lançamentos contábeis e trilha de auditoria — o que a trigger recusa e a política de integridade financeira proíbe. Anonimizar remove o dado pessoal sem falsificar nem destruir histórico contábil.

**O que a operação faz, exatamente:**

| Dado | Tratamento | Motivo |
| --- | --- | --- |
| `users.email` | Substituído por `deleted-<id>@market-pulse.invalid`, derivado do id e **nunca** do e-mail | Remove o dado pessoal; um hash do e-mail seria reidentificável por dicionário |
| `users` (nome) | Não se aplica | A tabela não tem coluna de nome, e o cadastro não pede nome |
| `users.password_hash` | Substituído por `deleted_placeholder_<uuid aleatório>` | Inutilizável; a coluna é `NOT NULL`, então nulo não é possível |
| `users.status` | `DELETED` | O login só procura `status='ACTIVE'` |
| Sessões no Redis | **Todas** as sessões do usuário, em todos os dispositivos | Ver "Revogação de sessões" abaixo |
| Tabela `sessions` do banco | `DELETE` sem efeito | A autenticação não usa essa tabela (pendência 5.7) |
| `watchlists` / `watchlist_items` | Removidos fisicamente (favoritos incluídos, são uma watchlist de sistema) | Preferência do usuário, não registro contábil nem auditoria |
| `portfolios` | `archived_at` preenchido e `name` neutralizado | Mantém o vínculo dos lançamentos; o nome é texto livre escolhido pelo usuário |
| `portfolio_events` | **Preservados, intocados** | Ledger append-only; exclusão e alteração são proibidas por trigger e por política |
| `portfolio_events.note` | Preservada | **Risco residual D3-A**, ver abaixo |
| `audit_logs` | Linha nova `USER_ACCOUNT_ANONYMIZED`; demais linhas preservadas | Trilha append-only, fora do expurgo (§5.1.1) |

**Revogação de sessões.** As sessões ficam só no Redis, em `auth:session:<hash do token>`, sem índice por usuário. A exclusão grava o marcador `auth:revoked_user:<id>` (TTL igual ao TTL de sessão) e varre as sessões do usuário. `RedisSessionStore.get` recusa qualquer sessão de usuário marcado, o que cobre também uma sessão criada durante a varredura. A revogação ocorre **antes** do commit: se o Redis estiver fora do ar, a anonimização inteira é desfeita (HTTP 500, nada muda) em vez de deixar outros dispositivos autenticados.

- Se qualquer etapa falhar **antes do commit**, o marcador é removido (`restore_user`). Sem isso, um usuário cuja conta não foi anonimizada ficaria bloqueado por 7 dias. As sessões já varridas não voltam: o usuário faz login de novo.
- Se o commit já ocorreu, o marcador permanece.
- Custo: um `EXISTS` extra por requisição autenticada (relevante para a cota de comandos de um Redis gerenciado) e uma varredura de chaves, proporcional ao total de sessões, a cada exclusão.
- `reset_demo` aceita `auth:revoked_user:` entre as chaves do cache DEMO; sem isso, qualquer exclusão de conta travaria a recriação do banco DEMO.

**Auditoria.** A linha é gravada **na mesma transação** da anonimização, então não existe anonimização sem registro. Campos: `entity_type='user'`, `entity_id` e `actor_user_id` = usuário anonimizado, `action='USER_ACCOUNT_ANONYMIZED'`, `resource='account'`, `result`, `request_id`. O `metadata` tem chaves fixas (`reason='LGPD_USER_REQUEST'`, `result`, `request_id`, `sessions_revoked`) e nunca recebe e-mail, nome de carteira, nota ou texto cru de exceção, que o driver pode preencher com o valor ofensor. Em falha, a linha registra `result='failed'` e `error_type`, em outra conexão.

**Risco residual D3-A: texto livre no ledger.** `portfolio_events.note` pode conter dado pessoal digitado pelo usuário e **não pode ser anonimizado** hoje: a trigger recusa qualquer `UPDATE`. O campo `idempotency_key`, definido pelo cliente, tem o mesmo problema com risco menor. Aceito para o beta fechado. **Antes de abrir o produto a outros usuários é obrigatória a ADR da opção B:** migration que permita **apenas** anular `note`, com a trigger verificando que nenhuma outra coluna mudou. A ADR da opção C (cifrar as notas com chave por usuário) fica como alternativa futura.

**Consequência aceita:** o `id` do usuário permanece como chave estrangeira em registros contábeis e de auditoria. Ele deixa de ser um identificador pessoal (não há e-mail, credencial ou sessão associados), mas não é removido, porque removê-lo quebraria a integridade do ledger.

**Cobertura.** Em `apps/api/tests/test_account_anonymization_day28.py`, sem banco nem Redis, com doubles que registram as chamadas: ordem das escritas (a auditoria é a última antes do commit), pseudônimo e hash inutilizável, nome da carteira neutralizado, ledger nunca tocado, metadata sem dado pessoal, remoção do marcador quando o commit falha, rollback total quando o Redis falha após o marcador, e export com strings decimais. Em Redis real (pula sem Redis): revogação em todos os dispositivos, sessão concorrente recusada e remoção do marcador. Também cobre a lista de chaves aceitas pelo reset do DEMO.

Os dois testes que gravam linhas de ledger, que a trigger append-only não permite apagar, exigem banco local descartável e opt-in explícito. São `test_account_deletion_anonymizes_and_preserves_append_only_ledger` (`test_hardening_day28.py`) e `test_anonymization_end_to_end_on_a_real_database` (`test_account_anonymization_day28.py`), este último cobrindo sessão de outro dispositivo, login recusado, linha de auditoria e carteiras. Eles recusam rodar contra o banco DEMO semeado e contra qualquer banco que não seja local:

```bash
MARKET_PULSE_ACCOUNT_LIFECYCLE=true \
MARKET_PULSE_ACCOUNT_LIFECYCLE_DATABASE_URL="postgresql://market_pulse:market_pulse_local_only@127.0.0.1:5432/market_pulse_restore_test" \
uv run --directory apps/api pytest -q tests/test_hardening_day28.py::test_account_deletion_anonymizes_and_preserves_append_only_ledger tests/test_account_anonymization_day28.py::test_anonymization_end_to_end_on_a_real_database
```

O SQL novo (renomear carteiras e inserir a auditoria) foi validado em PostgreSQL 16 real, numa transação sempre revertida. O teste ponta a ponta **ainda não foi executado** em banco local.

`GET /api/v1/account/data-export` retorna somente os dados do usuário autenticado (perfil, watchlists, carteiras e ledger próprios, incluindo as notas), escopado por `current_user.id`. Quantidades e valores saem como strings decimais, nunca `float`. O endpoint não declara `response_model`, então o contrato OpenAPI e o cliente TypeScript não mudam.

### 4.3 Resposta a Falhas de Dependências (Fail-Open vs. Fail-Closed)
- **Falha no Redis**:
  - Rotas de autenticação (`/api/v1/auth/login`, `/register`): **Fail-Closed** (retornam HTTP 503 com mensagem clara de serviço indisponível para prevenir bypass de brute-force).
  - Rotas públicas de cotação e diagnóstico (`/health`, `/api/v1/instruments`, `/market-data`): **Fail-Open** (continuam servindo leituras com rate limiter em memória local degradado gracioso).
- **Falha no PostgreSQL**:
  - Rotas com persistência retornam 503.
  - Rotas de cotação pública degradam para o estado `UNAVAILABLE` com conformidade à política de integridade de dados financeiros (nunca inventam cotações nem quebram o contrato OpenAPI).

---

## 5. Pendências registradas para o Dia 29

Itens identificados durante o Dia 28, **documentados e não resolvidos aqui**. Exigem autorização própria.

### 5.1 Ordem de `lint` e `build` no pipeline de CI
`eslint` deve nunca rodar depois de `next build`. `apps/web/tsconfig.json` inclui `.next/types/**/*.ts` e `.next/dev/types/**/*.ts`, e `eslint-config-next/typescript` usa lint tipado: com o diretório `.next` presente, o programa TypeScript passa a carregar a saída de build inteira e o processo morre com `FATAL ERROR: Zone Allocation failed - process out of memory`, mesmo com `.next/**` já listado em `globalIgnores`.

Hoje os workflows executam `lint → typecheck → test → build` nessa ordem e por isso nunca atingem o problema; ele aparece no ambiente local de quem roda `lint` após um `build`. A pendência é tornar essa ordem explícita e protegida no CI (ou isolar o `tsconfig` usado pelo lint), para que a garantia não dependa de coincidência de ordenação.

### 5.1.1 Decisão: `audit_logs` fica fora do expurgo
A rotina de retenção (`app/retention.py`) purga apenas registros operacionais: quarentena de market data, quarentena de ações corporativas, payloads brutos e agregados de Web Vitals. **`audit_logs` foi deliberadamente deixado de fora**, junto do ledger financeiro.

**Motivo:** `audit_logs` é trilha de auditoria append-only. Ela registra tentativas de acesso permitidas e negadas ao painel administrativo, eventos de revisão editorial e a própria exclusão de conta — inclusive os registros que sustentam a anonimização descrita em §4.2. Expurgar trilha de auditoria é decisão de compliance, com prazo próprio, e não decorre do prazo de retenção de dados operacionais. Aplicá-la de carona no mesmo `MARKET_PULSE_RETENTION_DAYS` apagaria evidência de auditoria por efeito colateral de uma configuração pensada para outra coisa.

`audit_logs` está em `PROTECTED_TABLES`, e `assert_plan_is_safe()` falha fechado se o plano de expurgo algum dia passar a nomeá-la. Definir retenção para auditoria é trabalho separado, que exige decisão explícita sobre prazo legal e destino dos registros (expurgo versus arquivamento frio).

### 5.2 Gate de segredos do próprio repositório estava vermelho — RESOLVIDO
**Status:** resolvido no commit `bb237f1` sem alterar a allowlist nem a lógica do scanner (a DSN fictícia dos testes passou a ser montada em runtime e o exemplo do runbook passou a ler a conexão do ambiente). O scanner também passou a detectar `rediss://` e URL Redis sem usuário (commit `d149e54`). O texto abaixo é o registro histórico do achado.

`python scripts/week1_gate.py secrets` saía com **exit 1** e apontava seis ocorrências. Nenhuma era segredo real:

- cinco em `apps/api/tests/test_hardening_day28.py`: uma DSN PostgreSQL fictícia cuja senha é `strong_real_pw_prod`, apontando para o host inexistente `prod.db`, usada nos testes que verificam a **rejeição** de configuração de produção;
- uma na seção 3.2 deste runbook: a DSN de exemplo do comando de restore, cuja senha é a palavra `senha`.

As ocorrências não são citadas aqui em forma completa de DSN, justamente para não gerar novos achados no scanner.

O scanner está correto: por desenho, só isenta as senhas-placeholder explícitas `local_only` e `market_pulse_local_only`, justamente para que nenhuma senha real passe despercebida. Como `ci.yml`, `day26-compliance.yml` e `day27-compliance.yml` executam esse gate, os três falhariam. A correção é trocar os dois valores pelos placeholders sancionados; não foi feita por estar fora do escopo autorizado desta execução.

### 5.3 Nenhuma execução de CI jamais teve sucesso
As 128 execuções registradas no GitHub Actions terminaram em `startup_failure` com 0s, incluindo as agendadas na `main`, muito antes desta branch existir. Actions está habilitado, os cinco arquivos de workflow são YAML válido e o repositório não está arquivado nem desabilitado. A causa provável é cota/cobrança de Actions em repositório privado, mas confirmar exigiria escopo `user` no token, o que implicaria novo login e não foi feito. **Consequência: não há evidência automatizada de suíte verde; o Dia 28 não pode ser fechado por CI enquanto isso não for resolvido.**

### 5.4 Link quebrado em `AGENTS.md` — RESOLVIDO
**Status:** resolvido no commit `7323532`. `AGENTS.md` agora aponta para `docs/CLAUDE.md`, que substituiu `docs/AGENTS.md` no rename aprovado. Registro histórico: a Definition of Done exige links relativos internos válidos.

### 5.5 Rastreabilidade do commit 296be6f
O commit `fix(security)` remove o endpoint `POST /portfolio-events` e, por dividir `routers.py` com trabalho anterior ainda não commitado, carrega também os endpoints de conta (`/account/data-export`, `DELETE /account`) e de telemetria. A mensagem do commit declara isso explicitamente no seu último parágrafo. O histórico não foi reescrito para separar os dois assuntos.

### 5.6 Fragilidade de ordem nos testes DEMO
`tests/test_demo_persistence_day24.py::test_revoked_demo_dataset_is_unavailable_and_reset_rejects_it` revoga o dataset DEMO e precisa rodar por último. O `demo-integration.yml` garante isso enumerando node ids na ordem correta, mas executar os arquivos inteiros quebra os demais testes do gate. A pendência é tornar a dependência de ordem explícita no próprio teste, em vez de depender da enumeração no workflow.

### 5.7 Tabela `sessions` não é usada pela autenticação
A tabela `sessions` existe no schema, mas a autenticação guarda sessões apenas no Redis. A única referência a ela no código da API é o `DELETE FROM sessions` da exclusão de conta, que portanto **não tem efeito**. Ele foi mantido para não mudar o escopo da correção. A pendência é decidir entre remover a tabela e o `DELETE` por uma migration (com ADR, por mexer no schema) ou passar a usá-la de verdade.

### 5.8 `test_demo_browser_day24` depende de Redis local não declarado
O teste fixa `redis://localhost:6379/15` e, sem Redis local, o rate limit (que falha fechado no login e roda antes do CSRF) devolve 503 no lugar do 403 esperado. Não há brecha: o login forjado é recusado de qualquer forma. Na execução na nuvem foi a única falha. Passa com Redis em `localhost`, o que a validação local confirmou (etapa E8).

### 5.9 `backup.py` e Redis gerenciado
`scripts/backup.py` chama `LASTSAVE` fora do `try`, e depois `BGSAVE`. São comandos administrativos que um Redis gerenciado pode recusar, o que abortaria o backup. Tratar antes do Dia 29.

### 5.10 Ordem entre CSRF e rate limit no `main.py`
Hoje o rate limit roda antes do CSRF, então a recusa por CSRF depende do Redis e uma requisição forjada consome cota. Decisão de segurança a discutir; não alterar sem ADR ou aprovação.

### 5.11 Expurgo real nunca executado
`app/retention.py` só teve o plano testado e um dry-run contra o banco DEMO. A primeira execução real (`dry_run=False`) ainda precisa de ensaio em banco descartável.

### 5.12 Ponta a ponta da anonimização ainda não executado
`test_anonymization_end_to_end_on_a_real_database` é opt-in e roda só em banco local descartável. Ainda não foi executado; está incluído nas etapas E2 e E12 do script local de validação.

### 5.13 ADR da opção B antes de abrir o produto
Ver risco residual D3-A em §4.2. A ADR (anular apenas `portfolio_events.note` sob trigger) é obrigatória antes de qualquer abertura a outros usuários.

---

## 6. Como rodar a suíte de backend na nuvem (Neon + Upstash)

Serve para máquinas sem memória para o Docker local. O CI continua usando os serviços Postgres e Redis do próprio workflow; nada nesta seção altera o CI. **Nenhum valor real aparece neste documento.**

### 6.1 O que criar
- **Neon**: na branch `dev`, um banco chamado exatamente **`market_pulse_test`**. Nunca na branch `production`, reservada ao Dia 29.
- **Upstash**: um banco Redis dedicado ao teste, com TLS, que **não** seja o do app nem o de produção.

### 6.2 O que preencher
No `apps/api/.env`, arquivo ignorado pelo Git, **nunca** impresso, colado em chat ou commitado:

| Variável | Formato |
| --- | --- |
| `MARKET_PULSE_TEST_DATABASE_URL` | `postgresql://<credenciais>@<host-direto-do-neon>/market_pulse_test?sslmode=require&channel_binding=require` |
| `MARKET_PULSE_TEST_REDIS_URL` | `rediss://<credenciais>@<host-do-upstash>:6379`, sem `/N` no final |

Use a conexão **direta** do Neon (host sem `-pooler`). Não aponte `MARKET_PULSE_DATABASE_URL` nem `MARKET_PULSE_REDIS_URL` para a nuvem: o `conftest.py` lê só as duas variáveis `MARKET_PULSE_TEST_*`, para que a URL de um app nunca vire alvo de teste por acidente.

### 6.3 Execução
```powershell
# 1) Migrations contra o banco de teste. O Alembic lê MARKET_PULSE_DATABASE_URL,
#    então ela recebe o valor do banco de teste só nesta sessão, sem imprimir.
cd apps/api
$env:MARKET_PULSE_DATABASE_URL = $env:MARKET_PULSE_TEST_DATABASE_URL
python -m uv run alembic upgrade head
Remove-Item Env:MARKET_PULSE_DATABASE_URL

# 2) Suíte completa
$env:PYTHONPATH = "."
python -m uv run pytest -q -rs
```
Se `MARKET_PULSE_TEST_DATABASE_URL` estiver só no `.env`, e não na sessão, exporte-a na sessão antes do passo 1 sem ler o arquivo.

### 6.4 Travas
- **Nome do banco**: se o banco não se chamar `market_pulse_test`, a suíte recusa rodar (`RuntimeError` no `conftest.py`). A suíte executa `TRUNCATE ... CASCADE` em `users`, `portfolios` e no ledger, então o alvo precisa ser descartável.
- **DEMO desligado**: o `conftest.py` fixa `MARKET_PULSE_DEMO_ENABLED=false`, para um `.env` local não mudar o catálogo.
- **Redis**: a fixture de limpeza apaga as chaves `rate_limit:*` do banco Redis apontado. Por isso ele não pode ser compartilhado.
- **TLS**: o psycopg e o Alembic aceitam `sslmode=require&channel_binding=require` como vem do Neon. O check de `/health/ready` usa asyncpg, que não conhece `channel_binding`; `_asyncpg_dsn` em `app/health.py` remove só esse parâmetro e mantém `sslmode`.
- Ao colar saída de teste em qualquer lugar, confira que não há host, usuário nem token.

### 6.5 O que esperar
Não existe número-alvo fixo: o total cresce a cada teste novo. O resultado esperado é **zero falhas além da conhecida abaixo** e os skips apenas dos testes opt-in.

- **Falha esperada na nuvem:** `test_demo_browser_day24::test_local_demo_preflight_is_explicit_and_external_origins_are_denied` (pendência 5.8). Ele fixa Redis em `localhost`; sem Redis local devolve 503 no lugar de 403.
- **Skips esperados (10):** testes que exigem banco local dedicado, listados com o motivo no `-rs`: migration regression (1), gates integrados do Dia 27 (2), persistência DEMO (4), reset DEMO (1), ciclo de vida da conta (2).

Evidência desta etapa: ver o status do Dia 28 no [README](../../README.md).

---

## 7. Validação DEMO local (Docker)

Cobre o que a nuvem não consegue: os testes opt-in, o gate de integração DEMO do CI, o teste que precisa de Redis local e o expurgo em dry-run. Replica o ambiente de `.github/workflows/demo-integration.yml` com os placeholders locais já versionados.

**Pré-condição crítica:** com `MARKET_PULSE_TEST_*` presentes no ambiente **ou** no `apps/api/.env`, a suíte aponta para a nuvem mesmo com Docker ligado. Antes de uma validação local, retire essas variáveis dos dois lugares.

Sequência, equivalente ao job `demo-idempotency`:

1. Subir só `postgres` e `redis` (`docker compose up -d --wait postgres redis`).
2. Recriar os bancos descartáveis `market_pulse_demo`, `market_pulse_migration_test` e `market_pulse_restore_test` e limpar apenas o Redis banco 15. O banco `market_pulse` nunca é tocado.
3. Exportar as variáveis do bloco `env` do job (`APP_ENV`, `MARKET_PULSE_ENVIRONMENT`, `MARKET_PULSE_DEMO_*`, `MARKET_PULSE_MIGRATION_*` e as URLs locais).
4. `alembic upgrade head` em `market_pulse_demo` e depois em `market_pulse_restore_test`; `python -m app.demo seed_demo`.
5. Rodar, com `-rs` e nesta ordem: `test_demo_browser_day24`; os dois testes DEMO que o CI não executa (`persistence` linhas 75 e 146); a regressão de migration; a sequência crítica do CI (seed idempotente, reset duas vezes, revogação por último, gates do Dia 27); e os dois testes de ciclo de vida da conta com `MARKET_PULSE_ACCOUNT_LIFECYCLE=true`.
6. Teste negativo: sem nenhuma variável de opt-in, os testes opt-in devem **continuar pulados** (10).
7. Expurgo: `purge_expired_records(dry_run=True)` contra `market_pulse_demo`, confirmando que `audit_logs` e `portfolio_events` não estão no plano e que as contagens não mudam.
8. `docker compose stop` ao final.

Não existe CLI `app.cli.retention`; o expurgo é chamado como função. O script usado na validação mora fora do repositório.

### 7.1 Resultado informado
Resultado informado pelo responsável pelo produto a partir do `resultado.log` local da validação E1–E13 (o log não está no repositório e não foi conferido por Claude Code): **todas as etapas OK**, 10 testes opt-in passando, teste negativo com 9 skipped e expurgo em dry-run com `audit_logs` intacto. Essa execução é anterior ao teste ponta a ponta da anonimização (pendência 5.12), que portanto ainda não foi exercitado em banco local.
