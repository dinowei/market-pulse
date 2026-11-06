# Core Web Vitals e bundle no ambiente real (Dia 38)

- **Data:** 2026-10-07 (UTC).
- **Fontes:** [roadmap](../ROADMAP_30_DAYS.md) (Dia 38), [diretriz](../design/PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md)
  §18 ("meça LCP, INP, CLS, bundle, frame time e cold load no ambiente real") e budgets do
  Dia 27 (`apps/web/performance/day27-fixtures.json`): P95 LCP 2.500 ms, INP 200 ms e
  CLS 0,10. **Nenhum budget foi relaxado.**

## 1. O que mudou no gate

O gate do Dia 27 comparava os budgets só com **amostras de fixture**, não com medição.
Agora `scripts/day27_performance_gate.mjs` também falha quando:

- uma medição real registrada em `apps/web/performance/day38-staging.json` passa de um
  budget, em qualquer perfil e rota;
- a primeira carga de qualquer rota do build atual passa do orçamento de bundle
  (`apps/web/performance/bundle-budget.json`).

O caminho de falha foi verificado: com o orçamento de JS reduzido a 150 KB, o gate falha
e lista as rotas.

## 2. Medição de laboratório no staging real

**Método:** `apps/web/performance/measure-vitals.mjs` (Playwright e Chromium), 5
execuções por rota, cada uma com contexto novo (cache frio). P95 por posto mais próximo;
com 5 execuções, é o máximo. O INP é de laboratório: a maior interação após um clique ou
tecla sintéticos.

**Alvo:** `https://market-pulse-staging.vercel.app`, branch `feature/dia-29-staging`,
commit `60df9ca` (código do Dia 29), API no Render já aquecida.

| Rota | Perfil | LCP P95 (ms) | CLS P95 | INP lab P95 (ms) | Dados prontos P95 (ms) | Long tasks P95 (ms) |
| --- | --- | --- | --- | --- | --- | --- |
| `/` | desktop | 568 | 0,024 | 32 | 1.957 | 132 |
| `/portfolios` | desktop | 808 | 0 | 24 | 799 | 0 |
| `/compare` | desktop | 764 | 0 | 24 | 755 | 0 |
| `/calendar` | desktop | 776 | 0 | 16 | 771 | 0 |
| `/login` | desktop | 448 | 0 | 32 | 523 | 0 |
| `/` | móvel | 964 | 0,002 | 40 | 2.578 | 220 |
| `/portfolios` | móvel | **2.252** | 0 | 32 | 2.327 | 241 |
| `/compare` | móvel | 1.916 | 0 | 88 | 2.022 | 268 |
| `/calendar` | móvel | **2.168** | 0 | 32 | 2.233 | 199 |
| `/login` | móvel | 688 | 0 | 64 | 1.503 | 278 |

Perfil móvel: 390 × 844, CPU 4× mais lenta e rede de 1,6 Mbit/s com 150 ms de latência
(emulação via CDP). Frame time P95 de 16,8 ms em todas as rotas, ou seja, um quadro a
60 Hz sem travamento após a carga. TTFB mediano entre 45 e 59 ms (página estática na
Vercel).

**Resultado:** todas as rotas ficam dentro dos três budgets nos dois perfis.

## 3. Cold load

| Medição (2026-10-07 04:16 UTC) | Tempo |
| --- | --- |
| Primeira chamada a `/health/live` com a API ociosa | **52.836 ms** |
| Chamadas seguintes | 297 ms e 638 ms |

O plano grátis do Render hiberna a instância sem tráfego. O primeiro visitante depois
de um período ocioso vê a página em menos de 1 s (LCP do HTML estático), mas espera cerca
de 53 s pelos dados, com os estados de carregamento visíveis.

## 4. Bundle (build atual da branch `feature/dia-31-34`)

`apps/web/scripts/bundle-audit.mjs` soma os scripts e estilos que cada HTML
pré-renderizado referencia:

| Rota | JS de primeira carga (KB gzip) | CSS (KB gzip) |
| --- | --- | --- |
| `/portfolios` | 185,2 | 6,1 |
| `/` | 180,5 | 6,1 |
| `/watchlists` | 177,4 | 6,1 |
| `/login` e `/register` | 176,2 | 6,1 |
| `/compare` | 173,8 | 6,1 |
| `/heatmap` | 173,5 | 6,1 |
| `/editorial/admin` | 172,9 | 6,1 |
| `/atlas` | 172,8 | 6,1 |
| `/admin/system` | 172,6 | 6,1 |
| `/calendar` | 172,5 | 6,1 |

Sete scripts, com 171,2 KB gzip, são comuns a todas as rotas: o runtime do Next, o React
e o layout raiz. O que é específico de cada rota fica entre 1,3 KB (`/calendar`) e
14,0 KB (`/portfolios`). Nenhum token de 3D ou WebGL no bundle (política P0 do Dia 27).
O orçamento de regressão foi fixado em 200 KB de JS e 10 KB de CSS por rota (cerca de 8%
acima do maior valor medido).

## 5. Achados

| # | Achado | Impacto | Encaminhamento |
| --- | --- | --- | --- |
| P-1 | Cold start de ~53 s da API no plano grátis do Render | Primeiro acesso após ociosidade sem dados por quase 1 min | Decisão de plano no Dia 39 (usuário), junto com Redis persistente e plano Vercel |
| P-2 | No perfil móvel, `/portfolios` e `/calendar` usam 87% a 90% do budget de LCP | Pouca margem para crescer | O elemento de LCP aparece depois da busca no cliente; renderizar a estrutura estável no servidor é o candidato, com nova medição |
| P-3 | A telemetria de campo guarda só soma e contagem diárias | Dá média, não P95; o budget é P95 | H-26: histograma por faixas exige mudança de contrato e ADR |
| P-4 | O banco do staging não aceita conexões externas | Os dados de campo não foram lidos nesta medição | Correto por segurança; a leitura fica pelo painel `/admin/system` do usuário |

## 6. Limitações

- O staging roda o código do Dia 29. As mudanças dos Dias 30 a 37 só podem ser medidas
  no ambiente real depois do deploy, que exige autorização do usuário.
- A máquina de medição tem 3,7 GB de RAM e estava sob pressão de memória; os números de
  CPU tendem a ser piores que os de um usuário real no mesmo perfil.
- Cinco execuções por rota dão um P95 grosseiro; a medição de campo (RUM) continua sendo a
  referência quando houver tráfego.
