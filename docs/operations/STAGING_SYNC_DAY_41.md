# Sincronização GitHub, Vercel e Render (Dia 41)

- **Data:** 2026-10-11.
- **Método:** somente leitura. Usei `git ls-remote`, a API do Render (serviço, deploys e
  logs), a API da Vercel (domínios, aliases, eventos de build e nomes de variáveis) e
  `curl` em rotas públicas.
- **Este documento não autoriza deploy.** Push em `feature/dia-29-staging` implanta a
  produção da Vercel. Toda ação remota exige autorização explícita do usuário.

## 1. Estado medido

| Item | Valor medido | Fonte |
| --- | --- | --- |
| `main` | `9cfb5c9` | `git ls-remote` |
| `feature/dia-29-staging` | `1747184` | `git ls-remote` |
| `feature/dia-41-sync` | `4916e5b` no início da auditoria | `git ls-remote` |
| Histórico | Linear: `main`, `60df9ca` e `1747184` são ancestrais de `4916e5b` | `git merge-base --is-ancestor` |
| Vercel, projeto | `market-pulse`, ligado a `dinowei/market-pulse` | API da Vercel |
| Vercel, produção | Deployment `dpl_AZLqS44X…`, branch `feature/dia-29-staging`, commit `1747184` | Log de build ("Cloning … Commit: 1747184") |
| Vercel, domínios de produção | `market-pulse-staging.vercel.app` e `market-pulse-nine-iota.vercel.app`; nenhum domínio próprio | Domínios do projeto |
| Vercel, preview de `feature/dia-41-sync` | Deployment `dpl_BkarhBDK…`, commit `4916e5b`, build concluído, protegido por login (302) | Log de build e `curl` |
| Vercel, variáveis (nomes) | `MARKET_PULSE_API_PROXY_ORIGIN` e `NEXT_PUBLIC_API_BASE_URL`, nos alvos produção e preview; valores sensíveis não lidos | API da Vercel |
| Render, serviço | `market-pulse-staging-api`, mesmo repositório, `rootDir: apps/api`, branch `feature/dia-29-staging`, deploy automático por commit, Blueprint (`render.yaml`) | API do Render |
| Render, deploy vivo | `dep-db5dmgdckfvc739rhfrg`, commit `1747184`, manual, 2026-10-11 00:41 UTC | API do Render |
| Migration no staging | `20260911_0011 → 20261005_0012` aplicada às 00:42:34 UTC | Log do Render |
| Smoke público | `/health/live` 200 (cold start de 42 s); catálogo com 5 itens; heatmap 200; proventos 404 e `/markets` 404 (rotas que só existem depois de `1747184`) | `curl` |

Conclusão: o staging está **alinhado em `1747184`**. Web e API estão no mesmo commit
desde o deploy manual de 2026-10-11, o que encerra o H-28. O código dos Dias 41 em diante
só existe no preview protegido da Vercel, que usa a mesma API do Render.

### Diretórios do monorepo

- **Render:** `rootDir: apps/api`, confirmado.
- **Vercel:** o diretório raiz não aparece nas ferramentas de leitura disponíveis. O build
  usa o `pnpm-lock.yaml` da raiz e terminou bem nos dois deployments. **Conferir no
  painel** antes da promoção.

## 2. Diferença entre o que está no ar e o candidato

| Área | `1747184` → candidato |
| --- | --- |
| Migrations | Nenhuma nova; a cabeça continua `20261005_0012` |
| `render.yaml`, `config.py`, `pyproject.toml`, `uv.lock`, `package.json`, `pnpm-lock.yaml` | Sem mudança |
| Contrato (OpenAPI) | Só acréscimos: `GET /market-data/corporate-actions/{canonical_id}`, `GET /portfolios/{id}/drawdown`, campo `drawdown` no overview |
| `next.config.ts` | Cabeçalho CSP em modo Report-Only (só observa) |
| Variáveis novas | Nenhuma obrigatória; `NEXT_PUBLIC_ATLAS_MOTION` é opcional (ausente = movimento ligado) |

Compatibilidade:

- **API nova com web antiga:** compatível, porque o contrato só acrescenta.
- **Web nova com API antiga:** degrada sem quebrar. O drawdown mostra "Indisponível" e os
  proventos mostram "Eventos indisponíveis: HTTP 404".
- **Ordem preferida:** API primeiro, depois a web.

## 3. Opções de alinhamento

| Opção | O que muda | Risco |
| --- | --- | --- |
| A. Vercel e Render passam a seguir `feature/dia-41-sync` | Branch de produção da Vercel e branch do serviço no Render | Duas mudanças de configuração. O Render é gerido pelo `render.yaml` (`branch: feature/dia-29-staging`), e uma sincronização do Blueprint pode desfazer a troca. O rollback também exige reconfigurar |
| **B. Avanço rápido de `feature/dia-29-staging` até o SHA do candidato** | Só a referência Git; nenhuma configuração | Um push dispara a Vercel (produção) e, em tese, o Render. Em 2026-10-07 o Render não implantou sozinho (H-28), então pode ser preciso o deploy manual. Há uma janela de minutos com web nova e API antiga, que degrada sem quebrar |
| C. Staging separado (segunda API no Render para o preview) | Novo serviço, variável de preview por branch na Vercel e origem de CORS nova | Mais recursos no plano grátis (horas de instância, banco compartilhado) e mais configuração. Útil só se o staging atual precisar ficar congelado |
| D. Promover o preview existente na Vercel | "Promote to Production" de `dpl_BkarhBDK…` | O Render só implanta commits da própria branch, então a API ficaria em `1747184`. Não alinha nada |

**Recomendação: B.** É o único caminho sem mudança de configuração, com uma só referência
para os dois serviços e rollback por deployment.

## 4. Passos da opção B (só com autorização)

1. Conferir o SHA e o avanço rápido:

   ```bash
   git fetch origin
   git merge-base --is-ancestor origin/feature/dia-29-staging <SHA> && echo avanco-rapido
   ```

2. Push do SHA, sem `--force`:

   ```bash
   git push origin <SHA>:refs/heads/feature/dia-29-staging
   ```

3. **Render:** conferir em Deploys se surgiu um deploy de `<SHA>`. Se não surgir em 5
   minutos, use "Manual Deploy → Deploy latest commit". Nesse momento esse botão
   representa `feature/dia-29-staging` em `<SHA>`; confira o SHA no deploy criado.
4. **Vercel:** conferir se o deployment de produção mostra "Commit: `<SHA>`" no log de build.
5. Validar:
   - os dois SHAs;
   - `/health/live`;
   - páginas `/`, `/markets`, `/assets?id=equity.br.b3.petr4`, `/compare`, `/portfolios`,
     `/account`, `/atlas` e `/heatmap`;
   - API: proventos 200 e `/instruments` com 7 itens;
   - login, watchlist e carteira com a conta do usuário;
   - logs do Render sem 5xx.

## 5. Rollback

- **Banco:** nenhuma migration entre `1747184` e o candidato, então o rollback não toca no
  banco.
- **Vercel:** "Instant Rollback" ou "Promote" do deployment `dpl_AZLqS44X…` (`1747184`).
- **Render:** "Rollback" para o deploy `dep-db5dmgdckfvc739rhfrg` (`1747184`).
- **Git:** não reescrever `feature/dia-29-staging`. Se for preciso voltar o código, usar um
  commit de reversão, também com autorização.

## 6. Execução da opção B (2026-10-11, autorizada pelo usuário)

| Passo | Resultado medido |
| --- | --- |
| Verificações antes do push | `1747184` é ancestral de `c3e77c0`; 19 commits sem merge; nenhum arquivo removido ou renomeado; nenhuma migration nova; testes não diminuíram (backend 311 → 334 funções, web 72 → 94, E2E 7 → 10); diff revisado, incluindo a retenção com limites (`4726b60`) |
| Push | `1747184..c3e77c0` em `feature/dia-29-staging`, avanço rápido, sem `--force`; `main` intacta em `9cfb5c9` |
| Vercel | Deployment de produção `dpl_DEzTYLsjnThoYGfWvrRamUCtMMrh`, log "Branch: feature/dia-29-staging, Commit: c3e77c0"; `/markets` respondeu 200 em 40 s |
| Render | **Não disparou.** Depois de 12 minutos, o deploy vivo continua `dep-db5dmgdckfvc739rhfrg` (`1747184`), e a rota de proventos ainda dá 404. O histórico de eventos do serviço não mostra build, deploy nem "commit ignored" para este push nem para o de 2026-10-07; os deploys desde 07/10 foram manuais ou por API (H-33) |
| Decisão | Promoção parada no Render, como o usuário pediu: sem deploy manual e sem a validação final enquanto web e API estiverem em commits diferentes |

**Estado resultante:** Vercel em `c3e77c0` e Render em `1747184`. A web nova degrada sem
quebrar. Os sinais visíveis da API antiga no staging:

- proventos e drawdown aparecem como indisponíveis;
- o catálogo tem 5 itens;
- os benchmarks mostram 0,00% ("estável"), o FLAT inventado já corrigido no código.

**Para alinhar (exige autorização):** "Manual Deploy → Deploy latest commit" no serviço
`market-pulse-staging-api`. Hoje esse botão representa `feature/dia-29-staging` em
`c3e77c0`; confira o SHA no deploy criado. Se o usuário autorizar antes a promoção de um SHA
mais novo, o mesmo botão passa a representar esse SHA.

## 7. Alinhamento em `fa6a95c` (2026-10-11, autorizado pelo usuário)

| Passo | Resultado medido |
| --- | --- |
| Verificações | `c3e77c0` é ancestral de `fa6a95c`; 7 commits sem merge; nenhum arquivo removido; nenhuma migration; `render.yaml`, configuração e `uv.lock` sem mudança |
| Push | `c3e77c0..fa6a95c` em `feature/dia-29-staging`, avanço rápido; `main` intacta |
| Render | O deploy automático não disparou (H-33). O usuário fez o deploy manual; a trava da sessão bloqueou o disparo pelo agente. Ficou no ar o deploy `dep-db5ph459fdbs73dm6040`, commit `fa6a95c`, às 14:10 UTC |
| Vercel | O deployment automático de produção (`dpl_9U1croGRo7hb27xEuESkNFj7voFU`) falhou em 3 s com "Git information retrieval failed for this deployment" (falha entre Vercel e GitHub, sem build). O usuário fez Redeploy em Production. Ficou no ar `dpl_3ZUYgcWrQGFjmSJibJri1EoZq27j`, com o log "Branch: feature/dia-29-staging, Commit: fa6a95c" |

**Validação remota (sem login, só leituras e uma requisição recusada):**

- **Health:** `/health/live`, `/health` (`environment: staging`) e `/health/ready` (`database: ok`, `cache: ok`) com 200; `/docs` com 404.
- **Páginas:** `/`, `/markets`, `/markets?tab=indices`, `/assets?id=equity.br.b3.petr4`, `/compare`, `/portfolios`, `/account`, `/atlas`, `/heatmap`, `/watchlists` e `/login` com 200.
- **API pelo proxy:**
  - catálogo com 7 itens;
  - benchmarks `DEMO`, com `change_percent` nulo e "Unidade não declarada";
  - VALE3 `UNAVAILABLE` com `DATASET_NOT_APPROVED`;
  - PETR4 `DEMO`/`STALE` com preço;
  - proventos `UNAVAILABLE` com `DATASET_NOT_APPROVED`;
  - histórico com `max_points` (antes 422), heatmap e lotes de cotação e histórico com 200.
- **Proteção:** sem sessão, `auth/me`, `GET` e `POST /watchlists` respondem 401; `POST` com origem estranha recebe 403 (CSRF).
- **Logs do Render desde 14:09 UTC:** nenhum 5xx. Os únicos avisos são do `uv` sobre `VIRTUAL_ENV`, inofensivos e anteriores.
- **Tela `/markets`:** 14 séries, nenhuma "estável" inventada, CMIN3, PETR4 e VALE3 na aba de ações.

**Não validado pelo agente:**

- login, logout, watchlist, carteira, drawdown e proventos com sessão, porque exigem a senha do usuário;
- CI (H-05) e os 10 testes opt-in de banco dedicado.

**Procedimento a partir de agora:** a cada promoção, conferir as duas plataformas. No
Render, o deploy é manual (H-33). Na Vercel, se aparecer "Git information retrieval
failed", usar Redeploy em Production.
