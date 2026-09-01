# Market Pulse Web — instruções locais

Estas regras complementam o `AGENTS.md` da raiz e nunca reduzem as exigências de segurança, política financeira, licenciamento ou roadmap.

## Leitura obrigatória

Antes de planejar, revisar ou alterar frontend, leia integralmente:

- `../../AGENTS.md`;
- `../../docs/engineering/ENTERPRISE_ENGINEERING_BASELINE.md`;
- `../../docs/design/PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md`;
- `../../docs/policies/FINANCIAL_CONTENT_POLICY.md`;
- `../../docs/ROADMAP_30_DAYS.md`;
- ADRs relevantes, especialmente ADR-005, ADR-006 e ADR-007;
- tipos gerados do contrato e o OpenAPI atual do backend.

O cliente canônico é `src/generated/api.ts`; regenere-o quando `docs/api/openapi.json` mudar.

Se uma fonte estiver ausente ou contraditória, pare e reporte; não invente substituição.

## Contrato visual e financeiro

- Preto, branco e cinzas são a identidade predominante. Dourado não é identidade, foco ou seleção.
- Verde é `UP`, vermelho é `DOWN` e azul é `FLAT`/referência; sempre use sinal, texto, ícone ou padrão adicional.
- Uma série real produz exatamente uma linha principal; várias linhas exigem várias séries reais.
- Comparações multissérie usam `INDEX_100` por padrão e mantêm valores reais, moeda, base, fonte e timestamps acessíveis.
- Preço bruto só aparece com moeda, unidade, calendário e metodologia compatíveis, ou FX aprovado.
- Não suavize além dos pontos, extrapole, esconda gaps, invente eventos ou transforme índice em preço.
- Carteiras são registros informativos próprios; cálculos vêm do domínio/backend, nunca de regra financeira duplicada no componente.
- Nunca gere compra/venda/manutenção, timing, alocação, preço-alvo, suitability ou retorno garantido.

## Contrato frontend–backend

- Use tipos gerados do OpenAPI; não duplique schemas nem use `any` para esconder incompatibilidade.
- Não invente endpoints, campos, pontos, notícias, eventos ou períodos.
- Preserve `actual_value` quando houver `normalized_value`.
- Exiba fonte, timestamp, moeda, unidade, `DataLevel`, `Freshness`, ajuste e limitações.
- `UNAVAILABLE` não é zero; `PARTIAL` não é total; `DEMO` nunca é real.

## Renderização e desempenho

- HTML/CSS/SVG são padrão para estrutura e UI acessível.
- Canvas 2D exige justificativa medida de densidade/desempenho e equivalente acessível.
- WebGL/Three.js é P1, feature-flagged, lazy-loaded e ausente do bundle P0/comum.
- Separe verdade financeira, apresentação, arte opcional e acessibilidade.
- Pause/reduza movimento com `prefers-reduced-motion`, fora da viewport e com documento oculto.

## Segurança e privacidade

- Sessões permanecem em cookie `HttpOnly`; nunca em `localStorage`/`sessionStorage`.
- Não exponha provider keys, cron secrets ou configuração interna.
- Siga estratégia aprovada de CSRF/Origin e autorização no backend.
- Sanitize conteúdo editorial; evite HTML arbitrário.
- Não registre carteiras, transações, credenciais, segredos ou PII desnecessária.

## Estados e verificação

Componentes conectados tratam explicitamente `loading`, `refreshing`, `empty`, erro recuperável/terminal, rate limit, signed-out, forbidden, `FRESH`, `STALE`, `DEMO`, `UNAVAILABLE`, `PARTIAL`, offline, provider outage e feature disabled.

Execute verificações relevantes: lint, typecheck, contrato, unit/component, Playwright, axe, teclado, zoom, regressão visual e medição de performance. Verifique uma série/uma linha, N séries/N linhas, matemática de `INDEX_100`, valores reais, cores semânticas, gaps e reduced motion. Não declare conclusão sem saída recente e diff revisado.
