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

python scripts/restore.py \
  --backup-dir /var/backups/market-pulse/20260927_100000 \
  --target-db-url "postgresql://usuario:senha@host:5432/market_pulse" \
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

`DELETE /api/v1/account` **anonimiza** o registro do usuário; não executa exclusão física da linha.

**Decisão:** anonimização com preservação do ledger.

**Justificativa:** `portfolio_events` é um ledger financeiro append-only protegido por trigger de banco (`prevent_immutable_portfolio_event_change`), e `audit_logs` é registro de auditoria. `portfolio_events.created_by` referencia `users.id`. Um hard delete exigiria apagar ou reescrever lançamentos contábeis e trilha de auditoria — o que a trigger recusa e a política de integridade financeira proíbe. Anonimizar remove o dado pessoal sem falsificar nem destruir histórico contábil.

**O que a operação faz, exatamente:**

| Dado | Tratamento | Motivo |
| --- | --- | --- |
| `users.email` | Substituído por `deleted-<id>@market-pulse.invalid` | Remove o dado pessoal, preserva integridade referencial |
| `users.password_hash` | Substituído por placeholder aleatório | Credencial deixa de existir; login torna-se impossível |
| `users.status` | `DELETED` | Estado terminal explícito |
| `sessions` | Excluídas (banco) e sessão revogada no Redis | Acesso encerrado imediatamente |
| `watchlists` / `watchlist_items` | Excluídos | Preferência do usuário, não registro contábil nem auditoria |
| `portfolios` | `archived_at` preenchido (não excluídos) | Mantém vínculo dos lançamentos ao portfólio |
| `portfolio_events` | **Preservados, intocados** | Ledger append-only; exclusão é proibida por trigger e por política |
| `audit_logs` | Preservados, mais um evento `account_deletion` | Trilha de auditoria é append-only |

**Consequência aceita:** o `id` do usuário permanece como chave estrangeira em registros contábeis e de auditoria. Ele deixa de ser um identificador pessoal (não há e-mail, credencial ou sessão associados), mas não é removido, porque removê-lo quebraria a integridade do ledger.

**Cobertura:** `test_account_deletion_anonymizes_and_preserves_append_only_ledger` em `apps/api/tests/test_hardening_day28.py` prova o comportamento contra PostgreSQL real. Por gravar uma linha de ledger que a trigger append-only não permite apagar, o teste exige banco local descartável e opt-in explícito:

```bash
MARKET_PULSE_ACCOUNT_LIFECYCLE=true \
MARKET_PULSE_ACCOUNT_LIFECYCLE_DATABASE_URL="postgresql://market_pulse:market_pulse_local_only@127.0.0.1:5432/market_pulse_restore_test" \
uv run --directory apps/api pytest -q tests/test_hardening_day28.py::test_account_deletion_anonymizes_and_preserves_append_only_ledger
```

O teste recusa explicitamente rodar contra o banco DEMO semeado, para não contaminá-lo.

`GET /api/v1/account/data-export` retorna somente os dados do usuário autenticado (perfil, watchlists, carteiras e ledger próprios), escopado por `current_user.id`.

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

### 5.2 Fragilidade de ordem nos testes DEMO
`tests/test_demo_persistence_day24.py::test_revoked_demo_dataset_is_unavailable_and_reset_rejects_it` revoga o dataset DEMO e precisa rodar por último. O `demo-integration.yml` garante isso enumerando node ids na ordem correta, mas executar os arquivos inteiros quebra os demais testes do gate. A pendência é tornar a dependência de ordem explícita no próprio teste, em vez de depender da enumeração no workflow.
