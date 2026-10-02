# Market Pulse — transferência de pendências do Dia 28 para o Dia 29

- **Data do registro:** 2026-10-01
- **Decisão de escopo:** decidida pelo usuário em 2026-10-01. Ver "Reconciliação
  autorizada do Dia 28" em [ROADMAP_30_DAYS.md](ROADMAP_30_DAYS.md).
- **Estado do Dia 28:** PARCIAL. Evidências, decisões e o restante das pendências em
  [PRODUCTION_RUNBOOK_DAY_28.md](operations/PRODUCTION_RUNBOOK_DAY_28.md).
- **Este documento não autoriza** deploy, login externo, contratação, provisionamento,
  push nem uso de dado ou provider real.

Cada pendência tem **origem**, **motivo**, **critério de pronto** e **prova hoje**.
"Prova hoje" separa o que foi medido por Claude Code do que foi apenas informado, e
marca como **NÃO VERIFICADO** o que ninguém conferiu na fonte.

## A. Transferidas por decisão de escopo

### H-01 Dockerfiles non-root e shutdown gracioso
- **Origem:** linha do Dia 28 em `ROADMAP_30_DAYS.md:96`, "Artefatos para Vercel (web) e Render (API), non-root e shutdown", com o gate "Smoke local equivalente passa".
- **Motivo:** não é validável sem ambiente com memória suficiente para construir imagens, e o plano de deploy ainda precisa confirmar se Vercel e Render exigem imagem. O repositório não tem nenhum Dockerfile.
- **Critério de pronto:** (a) decisão documentada, com fonte oficial, de que cada plataforma exige ou dispensa imagem; (b) se exigir, Dockerfiles que rodam como usuário não root, com imagem base escolhida em fonte oficial e com versão e evidência registradas (`AGENTS.md`); (c) shutdown gracioso demonstrado (o processo termina limpo ao receber o sinal de parada, sem requisição cortada); (d) smoke local equivalente executado e registrado, sem login nem deploy externo.
- **Prova hoje:** nenhuma. Nada foi criado nem testado.

### H-02 CSP do frontend Next.js
- **Origem:** runbook §5.15. Os cabeçalhos de segurança existem só na API.
- **Motivo:** uma CSP pode quebrar script inline e estilos; precisa ser validada em navegador, e o E2E ainda não passou sem ela.
- **Critério de pronto:** E2E (`demo.spec.ts` e `day27-a11y.spec.ts`) passando **sem** CSP; depois a CSP adicionada e o mesmo E2E, mais axe, passando **com** ela; nenhuma violação de CSP no console do navegador nos fluxos principais.
- **Prova hoje:** nenhuma para o frontend. Na API, os cabeçalhos foram medidos em servidor real.

## B. Infraestrutura e custo

### H-03 Redis de produção separado do Redis de teste
- **Origem:** configuração de testes na nuvem (`MARKET_PULSE_TEST_REDIS_URL`).
- **Motivo:** o Upstash atual, plano Free, é de **teste**. A fixture `_reset_rate_limit_state` apaga as chaves `rate_limit:*` do banco apontado e os testes gravam chaves de sessão, então ele não pode ser o Redis da aplicação.
- **Critério de pronto:** instância de produção distinta e nomeada como tal; nenhuma variável `MARKET_PULSE_TEST_*` aponta para ela; confirmação, na fonte oficial, da política de eviction e do plano; documentado qual banco/instância cada ambiente usa.
- **Prova hoje:** que o Redis de teste existe e funciona com a suíte, medido. A política de eviction e os limites do plano **NÃO VERIFICADO**.

### H-04 `backup.py` com Redis gerenciado
- **Origem:** runbook §5.9.
- **Motivo:** `LASTSAVE` e `BGSAVE` são comandos administrativos que um Redis gerenciado pode recusar.
- **Critério de pronto:** o tratamento de erro já feito no Dia 28 (saída explícita `REDIS_SNAPSHOT=NAO_SUPORTADO`, restante do backup continua) validado contra o **Redis gerenciado real**; decisão sobre se o Redis precisa de backup (é cache e lock não autoritativo, `AGENTS.md`) ou se o snapshot deve ser dispensado formalmente.
- **Prova hoje:** comportamento medido só com um Redis falso nos testes. Contra o Upstash real: **NÃO VERIFICADO**.

### H-05 GitHub: bloqueio de cobrança e `startup_failure` do CI
- **Origem:** runbook §5.3.
- **Motivo:** todas as execuções do GitHub Actions medidas (135 em 2026-10-01; o número cresce com as agendadas) terminaram em `startup_failure` com 0 s, inclusive as agendadas na `main`, antes da existência da branch do Dia 28. Não há evidência automatizada de suíte verde. O usuário informa bloqueio de cobrança de Actions e Codespaces.
- **Critério de pronto:** causa confirmada na fonte (configuração de cobrança do GitHub); uma execução do `ci.yml` concluída com sucesso, com saída vista; os workflows com `schedule` só habilitados depois disso.
- **Prova hoje:** os `startup_failure` e a contagem foram **medidos** (`gh run list`). A causa (cobrança) é **informada pelo usuário**; confirmar exigiria escopo `user` no token, o que implicaria novo login e não foi feito.

### H-06 Custo do `EXISTS` por requisição autenticada na cota do Upstash
- **Origem:** commit `7ec1792`. `RedisSessionStore.get` faz um `EXISTS` extra (marcador `auth:revoked_user:`) por requisição autenticada.
- **Motivo:** dobra, no pior caso, os comandos por requisição autenticada (`HGETALL` mais `EXISTS`), e o plano Free informado é de 500 mil comandos por mês.
- **Critério de pronto:** estimativa de comandos por mês com tráfego realista, comparada com a cota do plano vigente na fonte oficial; decisão entre manter, juntar as duas leituras num único comando ou usar outro mecanismo de revogação.
- **Prova hoje:** o custo extra é **medido por leitura do código**. A cota (500 mil) é **informada pelo usuário** e **NÃO VERIFICADO** na fonte.

### H-07 Limites e exigência de cartão de Render, Vercel e Cloudflare
- **Origem:** plano de deploy do Dia 29.
- **Motivo:** nenhum limite de plano, preço, exigência de cartão ou regra de uso foi conferido.
- **Critério de pronto:** cada fato conferido na documentação oficial da plataforma, com data da consulta, antes de qualquer contratação ou cadastro.
- **Prova hoje:** **NÃO VERIFICADO**. Nenhum número deste item deve ser tratado como fato.

## C. Segurança e produto

### H-08 ADR da opção B: anular `portfolio_events.note`
- **Origem:** decisão D3 de 2026-10-01 (opção A, risco residual documentado).
- **Motivo:** `note` é texto livre no ledger append-only e pode conter dado pessoal; hoje não pode ser anonimizado porque a trigger recusa qualquer `UPDATE`.
- **Critério de pronto:** ADR aceita; migration que permita **apenas** anular `note`, com a trigger verificando que nenhuma outra coluna mudou; teste provando que qualquer outra alteração continua recusada e que a anonimização passa a anular as notas. **Obrigatória antes de qualquer abertura do produto a outros usuários.**
- **Prova hoje:** o risco está documentado (runbook §4.2). Não há implementação.

### H-09 Ordem entre CSRF e rate limit no `main.py`
- **Origem:** runbook §5.10.
- **Motivo:** o rate limit roda antes do CSRF, então a recusa por CSRF depende do Redis e uma requisição forjada consome cota. É decisão de segurança.
- **Critério de pronto:** ADR com a decisão e o impacto; se a ordem mudar, testes cobrindo os dois lados (403 sem depender do Redis, e o rate limit continuando a proteger o login); sem relaxar o limite.
- **Prova hoje:** comportamento atual medido. Nenhuma mudança proposta.

### H-10 Tabela `sessions` sem uso pela autenticação
- **Origem:** runbook §5.7.
- **Motivo:** a autenticação guarda sessões só no Redis. O `DELETE FROM sessions` da exclusão de conta não tinha efeito; ver o registro do Dia 28 no runbook sobre o que foi removido. A tabela em si continua no schema.
- **Critério de pronto:** decisão entre remover a tabela por migration (com ADR, por mexer no schema, e atualizando a lista de tabelas do DEMO) ou passar a usá-la; teste cobrindo a decisão.
- **Prova hoje:** a ausência de outro uso foi **medida** por busca no repositório inteiro (ver runbook).

### H-11 `/auth/register` está aberto a qualquer pessoa
- **Origem:** leitura do código em 2026-10-01.
- **Motivo:** `POST /api/v1/auth/register` aceita cadastro **sem convite e sem verificação de e-mail** (`routers.py:169-179`; não há código de convite no backend). A verificação de e-mail está explicitamente fora do escopo no roadmap. O único freio é o rate limit de 5 tentativas por 60 s por IP.
- **Critério de pronto:** decisão registrada, antes de qualquer exposição, entre cadastro fechado (convite ou allowlist), desligar o endpoint na produção, ou aceitar cadastro aberto com as mitigações escolhidas; teste cobrindo a decisão.
- **Prova hoje:** a ausência de convite é **medida** por busca no código.

### H-12 Validação de produção recusa DEMO ligado: o que o staging exibe
- **Origem:** `validate_production_settings` (`app/core/config.py`), testada.
- **Motivo:** em `production` e `staging` o app recusa `MARKET_PULSE_DEMO_ENABLED=true`. Sem provider aprovado (`PUBLIC_APPROVED`) o produto não tem dado público a exibir, e DEMO não concede licença.
- **Critério de pronto:** decisão sobre o que o staging mostra sem provider aprovado (estado `UNAVAILABLE` explícito, ou aprovação de um provider conforme a matriz de licenças) e sobre se o staging deve aceitar DEMO; documentada e coberta por teste.
- **Prova hoje:** a recusa é **medida** em teste. A decisão de produto não existe.

### H-13 Morning Call e compliance
- **Origem:** política de conteúdo financeiro.
- **Motivo:** o Morning Call é conteúdo editorial; qualquer uso fora do uso pessoal precisa passar pelo compliance.
- **Critério de pronto:** revisão de compliance registrada antes de qualquer uso fora do uso pessoal; texto sem recomendação, sinal ou preço-alvo (`FINANCIAL_CONTENT_POLICY.md`).
- **Prova hoje:** o validador editorial automático existe e é testado. A revisão humana de compliance **não ocorreu**.

## D. Resultados que dependem da Rodada 2

### H-14 O E2E pode ter achado 429 real
- **Origem:** análise estática do E2E contra o rate limit (`middleware.py`, balde `standard`: 30 requisições por 60 s por IP).
- **Motivo:** contagem estática, sem telemetria: `demo.spec` teste 1 ≈ 26, teste 2 ≈ 20, `day27-a11y` ≈ 4 no mesmo balde, mais os POSTs de `web-vitals` (quantidade desconhecida). Pode haver 429 que derrube um fluxo legítimo.
- **Critério de pronto:** preencher **depois da Rodada 2** com o resultado real (`resultado_frontend.log`: contagem de 429 por caminho). Se houver 429 em fluxo legítimo, decisão de produto e segurança sobre o limite ou sobre o cliente, **sem relaxar o limite às cegas**.
- **Prova hoje:** **NÃO VERIFICADO**. É estimativa, não medição. Resultado real: _a preencher_.

## E. Pendências menores de teste e CI

### H-15 Ordem de `lint` e `build` no CI do frontend
- **Origem:** runbook §5.1.
- **Motivo:** o `tsconfig.json` do web inclui `.next/types`; rodar `eslint` depois de `next build` estoura memória. Hoje os workflows rodam `lint` antes, por coincidência de ordem.
- **Critério de pronto:** a ordem explícita e protegida no CI, ou o `tsconfig` do lint isolado da saída de build.
- **Prova hoje:** o estouro foi **medido** localmente. O CI nunca executou.

### H-16 Fragilidade de ordem nos testes DEMO
- **Origem:** runbook §5.6.
- **Motivo:** `test_revoked_demo_dataset_is_unavailable_and_reset_rejects_it` precisa rodar por último; só a enumeração de node ids no workflow garante isso.
- **Critério de pronto:** a dependência de ordem explícita no próprio teste.
- **Prova hoje:** **medida** (rodar os arquivos inteiros em outra ordem falhou).

### H-17 `test_demo_browser_day24` depende de Redis local não declarado
- **Origem:** runbook §5.8.
- **Motivo:** o teste fixa `redis://localhost:6379/15`; sem Redis local o rate limit devolve 503 antes do CSRF responder 403. Não há brecha. É a única falha na suíte na nuvem.
- **Critério de pronto:** o teste declara essa dependência de forma explícita, ou deixa de depender dela, sem alterar o comportamento de segurança.
- **Prova hoje:** **medida** na nuvem; passou com Redis local na validação informada.

### H-18 Dívida de lint e formatação preexistente
- **Origem:** `ruff` executado pelo ambiente do projeto em 2026-10-01, após o commit `3a3d940`.
- **Motivo:** `ruff check .` em `apps/api` acusa **82 erros** (78 E501 e 4 I001), **todos em `migrations/`**; `app` e `tests` estão limpos. `ruff format --check .` aponta **23 arquivos** fora do formato (migrations, `env.py`, `admin/system.py`, `market_data/comparison.py`, `portfolios/day27.py`, `portfolios/income.py` e alguns testes do Dia 25 em diante). Os arquivos alterados no Dia 28 foram formatados no commit `3a3d940`.
- **CI:** `ci.yml` roda `ruff check apps/api/app apps/api/tests` (e os workflows dos Dias 26 e 27 rodam `ruff check app tests`). Nenhum workflow roda `ruff format --check` nem `ruff check` em `migrations/`; portanto o gate atual **não falharia** por esta dívida. Se o gate for ampliado para o projeto inteiro, falhará até esta pendência fechar.
- **Critério de pronto:** `ruff check .` e `ruff format --check .` limpos no projeto inteiro, em commit dedicado só de lint/formatação (sem mudança de comportamento, migrations incluídas apenas se o histórico Alembic não for alterado em semântica), com a suíte completa verde depois.
- **Prova hoje:** **medida** (contagens acima). Não corrigido agora, por decisão de escopo.

### H-19 Limite de requisições por sessão nas rotas autenticadas (opção B)
- **Origem:** achado do E2E de 2026-10-01 (runbook §5.17).
- **Motivo:** o balde `standard` é por IP; usuários atrás do mesmo NAT dividem 30 requisições por 60 s. Limite por sessão exige a chave de sessão no middleware (que roda antes da autenticação) e decisão sobre o IP como segunda chave.
- **Critério de pronto:** decisão registrada (ADR se mudar a política); testes: um usuário não consome o balde de outro no mesmo IP, e o 31º pedido continua barrado; sem relaxar o limite.
- **Prova hoje:** **não verificado**; é análise de código, sem medição.

### H-20 `Retry-After` do 429 não é legível pelo navegador
- **Origem:** frontend de 429 do Dia 28 (runbook §5.17).
- **Motivo:** o 429 envia `Retry-After`, mas `main.py` expõe só `X-Request-ID` em `expose_headers` do CORS; o navegador não lê o cabeçalho entre `localhost:3000` e `:8000`. O frontend já usa o valor se vier, e senão mostra "aguarde alguns segundos". Além disso o valor enviado é sempre a janela (60), não o tempo restante.
- **Critério de pronto:** decisão sobre expor `Retry-After` no CORS (mudança de configuração de segurança, com teste) e sobre enviar o tempo restante real.
- **Prova hoje:** **medida** por leitura de `main.py:35-41` e `middleware.py`; não testada no navegador.

## F. Não transferidas: continuam abertas no Dia 28

Estas não vão para o Dia 29; sem elas o Dia 28 não fecha.

- **Rodada 1** (`run_local.ps1`, validação local com Docker): inclui o teste ponta a ponta da anonimização de conta em banco local e o dry-run do expurgo no DEMO. **Não executada** depois das últimas mudanças.
- **Rodada 2** (`run_frontend.ps1`, E2E no navegador): **não executada**.
- **Push autorizado** da branch `feature/dia-28-hardening`: não feito; sem autorização.
- **ADR da opção B** (H-08): obrigatória antes de abrir o produto a outros usuários; consta aqui por constar também na lista de transferidas.
