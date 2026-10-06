# Market Pulse — transferência de pendências do Dia 28 para o Dia 29

- **Data do registro:** 2026-10-01
- **Decisão de escopo:** decidida pelo usuário em 2026-10-01. Ver "Reconciliação
  autorizada do Dia 28" em [ROADMAP_30_DAYS.md](ROADMAP_30_DAYS.md).
- **Estado do Dia 28:** FECHADO em 2026-10-01 (decisão do usuário). Evidências, decisões e o restante das pendências em
  [PRODUCTION_RUNBOOK_DAY_28.md](operations/PRODUCTION_RUNBOOK_DAY_28.md).
- **Este documento não autoriza** deploy, login externo, contratação, provisionamento,
  push nem uso de dado ou provider real.

## Estado em 2026-10-05: bloqueadores do staging privado

Classes: **A** bloqueia o deploy do staging privado; **B** pode ser feito depois do
deploy; **C** é obrigatório antes de abrir o produto a outras pessoas.

| Item | Classe | Estado |
|---|---|---|
| H-01 imagem | A | Resolvido: imagem dispensada. Shutdown pendente do smoke. |
| H-03 Redis | A | Decidido: Render Key Value grátis (R2). |
| H-07 limites | A | Pesquisado com fonte oficial. |
| H-11 cadastro | A | Resolvido em código: fechado por padrão. |
| H-12 DEMO no staging | A | Decidido: sem DEMO, `UNAVAILABLE` explícito. |
| Cookie entre sites | A | Resolvido: [ADR-008](adr/008-same-origin-api-proxy.md), proxy same-origin. |
| `/docs` público | A | Resolvido: fechado em `production`/`staging`. |
| H-08, H-09, convite no cadastro (H-11) | C | Agendados para o Dia 30 (decisão do usuário, 2026-10-05). |
| H-13, H-19, H-21 | C | Agendados para o Dia 35. |
| H-23, Redis persistente, plano Vercel | C | Agendados para o Dia 39. |
| Demais itens | B | Abertos. |

O que falta para o deploy depende do usuário (push, contas e painéis) e segue o
[runbook do staging](operations/STAGING_RUNBOOK_DAY_29.md).

Cada pendência tem **origem**, **motivo**, **critério de pronto** e **prova hoje**.
"Prova hoje" separa o que foi medido por Claude Code do que foi apenas informado, e
marca como **NÃO VERIFICADO** o que ninguém conferiu na fonte.

## A. Transferidas por decisão de escopo

### H-01 Dockerfiles non-root e shutdown gracioso
- **Origem:** linha do Dia 28 em `ROADMAP_30_DAYS.md:96`, "Artefatos para Vercel (web) e Render (API), non-root e shutdown", com o gate "Smoke local equivalente passa".
- **Motivo:** não é validável sem ambiente com memória suficiente para construir imagens, e o plano de deploy ainda precisa confirmar se Vercel e Render exigem imagem. O repositório não tem nenhum Dockerfile.
- **Critério de pronto:** (a) decisão documentada, com fonte oficial, de que cada plataforma exige ou dispensa imagem; (b) se exigir, Dockerfiles que rodam como usuário não root, com imagem base escolhida em fonte oficial e com versão e evidência registradas (`AGENTS.md`); (c) shutdown gracioso demonstrado (o processo termina limpo ao receber o sinal de parada, sem requisição cortada); (d) smoke local equivalente executado e registrado, sem login nem deploy externo.
- **Prova hoje:** nenhuma. Nada foi criado nem testado.
- **Atualização de 2026-10-05:**
  - (a) Decidido, com fonte oficial: o staging **dispensa imagem**. O Render roda FastAPI no runtime Python nativo e a Vercel faz o build do Next.js nativamente (links no [runbook do staging](operations/STAGING_RUNBOOK_DAY_29.md)). Portanto (b) não se aplica ao staging; Dockerfile só volta a ser avaliado se uma plataforma passar a exigir imagem.
  - (c) e (d): o Render envia SIGTERM com shutdown delay padrão de 30 s; a demonstração do encerramento limpo ficou como passo 7 do smoke do staging. **Pendente** até o primeiro deploy.

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
- **Decisão do usuário (2026-10-01), staging privado:** o Redis do staging será o **Render Key Value grátis** (opção R2), que **não tem persistência** (ver H-07). Fica aceito que sessões e contadores de rate limit podem zerar em restart, por ser staging privado de 1 usuário. A suíte da nuvem continua no Upstash atual, sem mudança. Nenhuma variável `MARKET_PULSE_TEST_*` pode apontar para o Key Value do staging.
- **Pendência obrigatória antes de abrir o produto a outras pessoas:** migrar para Redis persistente, ou com Upstash pay-as-you-go num banco novo (R1, exige cartão), ou com a suíte da nuvem passando a usar Redis local e o banco Upstash Free virando o de produção (R3). A escolha deve ser registrada.

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
- **Atualização de 2026-10-01 (decisão do usuário):** o workflow agendado `market-pulse-refresh` (cron a cada 15 min) é desabilitado pelo usuário **pela interface do GitHub**, sem mudança de código. Só deve ser reativado depois de uma execução do `ci.yml` concluída com sucesso. A desabilitação é **informada pelo usuário**, não verificada por Claude Code.
- **Decisão do usuário (2026-10-01), cron do staging:** opção C4, **sem cron no staging**. O refresh é disparado manualmente, e o `market-pulse-refresh` continua desabilitado. Motivos: sem provider `PUBLIC_APPROVED` (H-12) o refresh só roda em `DRY_RUN` sobre DEMO; as alternativas pesquisadas no H-07 têm restrições (Vercel Hobby uma vez por dia, Render Cron pago, Cloudflare Free com 10 ms de CPU). Além disso, um cron frequente manteria a API grátis do Render acordada e consumiria a cota mensal de horas.

### H-06 Custo do `EXISTS` por requisição autenticada na cota do Upstash
- **Origem:** commit `7ec1792`. `RedisSessionStore.get` faz um `EXISTS` extra (marcador `auth:revoked_user:`) por requisição autenticada.
- **Motivo:** dobra, no pior caso, os comandos por requisição autenticada (`HGETALL` mais `EXISTS`), e o plano Free informado é de 500 mil comandos por mês.
- **Critério de pronto:** estimativa de comandos por mês com tráfego realista, comparada com a cota do plano vigente na fonte oficial; decisão entre manter, juntar as duas leituras num único comando ou usar outro mecanismo de revogação.
- **Prova hoje:** o custo extra é **medido por leitura do código**. A cota (500 mil) é **informada pelo usuário** e **NÃO VERIFICADO** na fonte.

### H-07 Limites e exigência de cartão de Render, Vercel e Cloudflare
- **Origem:** plano de deploy do Dia 29.
- **Motivo:** nenhum limite de plano, preço, exigência de cartão ou regra de uso foi conferido.
- **Critério de pronto:** cada fato conferido na documentação oficial da plataforma, com data da consulta, antes de qualquer contratação ou cadastro.
- **Prova hoje:** documentação oficial consultada em 2026-10-01 por Claude Code, sem criar conta nem fazer login. Os valores mudam: confira de novo antes de qualquer cadastro ou contratação. "Não encontrado" significa que não estava na fonte oficial consultada.
  - **Render:**
    - Há instâncias grátis de web service, Postgres e Key Value.
    - Web service grátis "dorme" após 15 min sem tráfego e volta em cerca de 1 min.
    - A cota é de 750 horas grátis por workspace por mês; esgotada, os serviços são suspensos até o mês seguinte. Fonte: <https://render.com/docs/free>.
    - O Key Value grátis roda Valkey 8, compatível com Redis, e **não tem persistência**: os dados se perdem em restart. Fonte: <https://render.com/docs/key-value>.
    - Cron Job é pago, com mínimo de US$ 1 por mês por job; a frequência mínima não é documentada. Fonte: <https://render.com/docs/cronjobs>.
    - Cartão: "No credit card is required" aparece apenas num artigo do site oficial (<https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026>), não nas docs. Nas docs: não encontrado.
  - **Vercel:**
    - Hobby é grátis e **restrito a uso pessoal e não comercial**. Qualquer uso profissional ou comercial exige plano pago e passa pelo compliance (H-13).
    - O cartão aparece só no upgrade para Pro. Fonte: <https://vercel.com/docs/plans/hobby>.
    - Cron no Hobby roda no máximo uma vez por dia, com precisão de ±59 min. Fonte: <https://vercel.com/docs/cron-jobs/usage-and-pricing>.
    - A Vercel não tem Redis próprio: usa integrações do Marketplace, e o antigo Vercel KV foi migrado para o Upstash. Fonte: <https://vercel.com/docs/redis>.
    - Comportamento de cold start: não encontrado.
  - **Cloudflare:**
    - Workers Free tem 100 mil requisições por dia; KV grátis tem 1 GB e não é Redis. Fonte: <https://developers.cloudflare.com/workers/platform/pricing/>.
    - Cron Triggers: 5 por conta no Free e 10 ms de CPU por execução; intervalo mínimo não encontrado. Fonte: <https://developers.cloudflare.com/workers/platform/limits/>.
    - Exigência de cartão e oferta compatível com Redis: não encontradas.
  - **Upstash:**
    - Free: 1 banco por conta, 500 mil comandos por mês, 256 MB e sem cartão. Isso confirma a cota citada no H-06.
    - Pay-as-you-go: US$ 0,20 por 100 mil comandos e exige cartão. Fonte: <https://upstash.com/pricing/redis>.
    - Cold start: não encontrado.

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
- **Resolvido em 2026-10-05 (decisão técnica delegada pelo usuário):** cadastro **fechado por padrão** em `production`/`staging`. `registration_open` (`app/core/config.py`) devolve falso nesses ambientes, salvo `MARKET_PULSE_REGISTRATION_ENABLED=true` explícito, e o endpoint responde 404. Local e test continuam abertos. O fluxo da conta única do staging está no [runbook](operations/STAGING_RUNBOOK_DAY_29.md), §6. Testes: `tests/test_staging_day29.py`. Antes de abrir o produto ainda é preciso decidir convite ou allowlist.

### H-12 Validação de produção recusa DEMO ligado: o que o staging exibe
- **Origem:** `validate_production_settings` (`app/core/config.py`), testada.
- **Motivo:** em `production` e `staging` o app recusa `MARKET_PULSE_DEMO_ENABLED=true`. Sem provider aprovado (`PUBLIC_APPROVED`) o produto não tem dado público a exibir, e DEMO não concede licença.
- **Critério de pronto:** decisão sobre o que o staging mostra sem provider aprovado (estado `UNAVAILABLE` explícito, ou aprovação de um provider conforme a matriz de licenças) e sobre se o staging deve aceitar DEMO; documentada e coberta por teste.
- **Prova hoje:** a recusa é **medida** em teste. A decisão de produto não existe.
- **Decisão de 2026-10-05 (técnica, delegada pelo usuário):** o staging roda **sem DEMO e sem provider**. Os dados de mercado devem aparecer como `UNAVAILABLE` explícito, sem cotação inventada. A recusa de DEMO em staging continua (a DEMO é só local, Dia 24). A conferência está no passo 6 do smoke do [runbook](operations/STAGING_RUNBOOK_DAY_29.md). Exibir dados reais exige provider `PUBLIC_APPROVED` na [matriz de licenças](DATA_PROVIDER_LICENSE_MATRIX.md).

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
- **Prova hoje:** a estimativa acima era estática. **Resultado real:** a Rodada 2 (`run_frontend.ps1`, 2026-10-01 22:02) terminou com E2E 6 passed e **nenhuma resposta 403, 429 ou 5xx**, executada e informada pelo responsável, com log fora do repositório. A margem do balde `standard` continua apertada (H-19, H-21).

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
- **CI:** apenas `day27-compliance.yml` roda Playwright, e só `e2e/day27-a11y.spec.ts` (cerca de 4 requisições no balde standard, abaixo de 30). O E2E `demo.spec.ts` não roda em nenhum workflow. Se ele passar a rodar no CI, precisará do mesmo espaçamento do `run_frontend.ps1` ou do limite por sessão.

### H-20 `Retry-After` do 429 não é legível pelo navegador
- **Origem:** frontend de 429 do Dia 28 (runbook §5.17).
- **Motivo:** o 429 envia `Retry-After`, mas `main.py` expõe só `X-Request-ID` em `expose_headers` do CORS; o navegador não lê o cabeçalho entre `localhost:3000` e `:8000`. O frontend já usa o valor se vier, e senão mostra "aguarde alguns segundos". Além disso o valor enviado é sempre a janela (60), não o tempo restante.
- **Critério de pronto:** decisão sobre expor `Retry-After` no CORS (mudança de configuração de segurança, com teste) e sobre enviar o tempo restante real.
- **Prova hoje:** **medida** por leitura de `main.py:35-41` e `middleware.py`; não testada no navegador.

### H-21 Reduzir requisições do frontend ao balde standard
- **Origem:** achado do E2E de 2026-10-01 (runbook §5.17).
- **Motivo:** o fluxo principal do E2E usa **26 das 30** requisições do balde standard por janela de 60 s, um usuário real fica perto do limite. Causas lidas no código: cada mutação de watchlist faz `load()` e recarrega a lista inteira (2 requisições por ação); `/portfolios` faz 1 lista + 8 detalhes por carga (9); a home faz 2 (Morning Call).
- **Critério de pronto:** sem refetch completo após cada mutação de watchlist; endpoint em lote para os detalhes de `/portfolios` (contrato OpenAPI e cliente gerado atualizados, sem editar o cliente à mão); contagem por fluxo medida de novo, sem relaxar o limite de 30.
- **Prova hoje:** contagem por **leitura de código**, não medida em execução.

### H-22 `/compare` abre em estado de erro com DEMO ligado
- **Origem:** defeito do Dia 26 encontrado pelo E2E do Dia 28 em 2026-10-01 (execução das 22:59, informada pelo responsável). O `/compare` usa ids padrão fixos (`equity.br.b3.petr4`) que não existem no catálogo DEMO, e com DEMO ligado a página abre em estado de erro (`404 POST /api/v1/market-data/history/batch`).
- **Direção preferida:** ids padrão escolhidos a partir do catálogo disponível (não hardcode de ids DEMO), funcionando tanto em DEMO quanto com provider real.
- **Decisão em aberto:** o batch deve devolver resultado parcial (série marcada como indisponível) em vez de 404 total quando um id falha? Isso mexe em contrato OpenAPI e exige decisão.
- **Critério de pronto:** `/compare` mostra a comparação por padrão no DEMO, e o E2E afirma o CONTEÚDO (não só a acessibilidade da tela de erro).
- **Prova hoje:** causa **lida no código** (`multi-asset-comparison.tsx:11`, `instruments/catalog.py:152-157`, `routers.py:535-536`); o 404 foi **informado** pelo responsável a partir do log. Sem risco de segurança.
- **Nota de 2026-10-05:** `GET /api/v1/instruments` é hoje um stub que devolve `items=[]` (`routers.py`, `list_instruments`), embora o contrato (`limit`, `offset`, `sort`, `order` e `InstrumentList`) já exista. Implementá-lo com o catálogo é o caminho natural para os ids padrão do `/compare`. Antes, comparar `docs/api/openapi.json` e rodar `npm run generate:api` se o contrato mudar. Classe B: não bloqueia o staging privado. Patches equivalentes preparados numa sessão na nuvem não chegaram a esta máquina e não foram usados.

### H-23 IP real do cliente atrás de proxies (rate limit)
- **Origem:** revisão do Dia 29 ([ADR-008](adr/008-same-origin-api-proxy.md)).
- **Motivo:** o rate limit e o limitador de autenticação usam `request.client.host` (`middleware.py`, `routers.py:_client_ip`). Atrás do proxy do Render, e ainda mais com o proxy da Vercel, esse valor tende a ser o do intermediário. Isso faz todos os clientes dividirem o mesmo balde. **Suposição**: o comportamento real não foi medido.
- **Critério de pronto:** medir no staging qual IP chega à API; decisão registrada (ADR se mudar a política) sobre quais cabeçalhos de proxy confiar e de quais origens, sem aceitar `X-Forwarded-For` arbitrário; testes provando que um cliente não forja o IP e que o 31º pedido continua barrado.
- **Classe:** C. Aceitável num staging de um único usuário; **obrigatório antes de abrir o produto**. Relacionado a H-09 e H-19.
- **Prova hoje:** leitura de código; nenhuma medição.
- **Medido em 2026-10-06 no staging (piora o diagnóstico):** o IP do cliente **era forjável**. Um `X-Forwarded-For: 203.0.113.77` enviado pelo cliente virou `request.client.host`, porque o Uvicorn confia nos cabeçalhos de proxy e o proxy do Render não filtra o valor do cliente. Isso permitia contornar o limite de login. **Mitigação aplicada:** [ADR-012](adr/012-untrusted-proxy-headers.md), Uvicorn com `--no-proxy-headers` (forja reproduzida localmente e eliminada com a flag). A solução definitiva, IP real por saltos confiáveis com testes de forja, continua no Dia 39.

## F. Itens que impediam o fechamento do Dia 28 (resolvidos em 2026-10-01)

- **Rodada 1** (`run_local.ps1`) e **Rodada 2** (`run_frontend.ps1`): executadas e informadas pelo responsável, ambas OK (ver runbook §5.19).
- **Push** da branch `feature/dia-28-hardening`: autorizado pelo usuário em 2026-10-01, somente para esse branch.
- **ADR da opção B** (H-08): **continua aberta**; obrigatória antes de abrir o produto a outros usuários.
