# Market Pulse — Diretriz Permanente de Frontend Particle Atlas

**Status:** normativa
**Versão:** 2.0
**Produto:** terminal financeiro informativo, analítico e educacional
**Direção visual:** Cláudio
**Implementação e integração:** Codex
**Aprovação final:** responsável humano pelo produto

Regra superior: aparência nunca prevalece sobre exatidão, licença, segurança, acessibilidade, desempenho ou rastreabilidade.

## 1. Finalidade e gatilhos

Leia esta diretriz integralmente antes de planejar, revisar ou modificar `apps/web/**`, páginas, layouts, componentes, tokens, dashboard, busca, páginas de instrumento, watchlists, carteiras próprias, Morning Call, gráficos, comparações, performance, Canvas, SVG, animação, WebGL, OpenAPI consumido pelo frontend, preço, patrimônio, FX, eventos, `DataLevel`, `Freshness`, provenance, responsividade, acessibilidade, performance ou estados `loading`, `empty`, `error`, `stale`, `demo`, `unavailable`, `partial`, Heatmap, Global Atlas, malha, topografia, partículas ou globo.

Para tarefas fora desses gatilhos, esta diretriz não amplia o escopo autorizado.

### Estado real após o Dia 19

Este documento é uma diretriz permanente de design do Market Pulse. Ele nasceu
no Dia 1 como especificação visual, mas deve ser lido conforme o estado atual do
projeto: já existem shell Particle Atlas, temas escuro/claro, gráfico P0 em SVG,
autenticação, sessões opacas, watchlists e favoritos privados. Ainda não existem
provider real, dado real, carteira, P&L ou TWR implementados. A nota
[Reconciliação visual do Dia 18.1](PARTICLE_ATLAS_VISUAL_RECONCILIATION_DAY_18_1.md)
registra esta atualização documental.

## 2. Ordem de precedência

Em conflito, prevalecem: política financeira, segurança, privacidade e licença; `PROJECT_SPEC.md` e `ROADMAP_30_DAYS.md`; ADRs aceitas; OpenAPI e comportamento comprovado do backend; esta diretriz; orientações complementares de Cláudio; imagens de referência apenas como inspiração. Não escolha silenciosamente: registre fonte, conflito, impacto e opção segura e peça decisão humana.

## 3. Objetivo do produto

O Market Pulse organiza dados de mercado, histórico, contexto e carteiras próprias para que o usuário compreenda o que aconteceu com ativos suportados. Pode exibir preços, históricos, variações, índices, ETFs, FIIs, fundos autorizados, benchmarks, patrimônio, P&L, proventos, performance factual, eventos permitidos e Morning Call factual.

Carteiras são registros informativos próprios. O produto não faz gestão de carteira, recomendação, suitability, execução, alocação sugerida ou promessa de retorno.

Carteiras pessoais são P0 do beta, mas ainda serão implementadas em dias
posteriores. Quando entrarem, o gráfico representará dinheiro real do usuário,
com preço médio ponderado, moeda de consolidação documentada para carteiras
BR/US, FX utilizado, provenance completa e marcadores somente para eventos reais
do ledger. A tabela equivalente será obrigatória.

## 4. Fronteira financeira permanente

É proibido recomendar compra, venda ou manutenção; sugerir timing/alocação; produzir preço-alvo; emitir sinal; prometer retorno; apresentar previsão como certeza; ranquear como “melhor investimento”; usar urgência; ou apresentar `DELAYED`, `EOD`, `DEMO`, `STALE` ou `PARTIAL` como tempo real, fresh ou completo.

Linguagem aceitável: “O ativo variou X% no período indicado.”, “O resultado factual da carteira foi X conforme os eventos registrados.”, “O cenário é condicional e pode mudar.” e “Não há dados suficientes para apresentar este valor.”

Aviso visível obrigatório: **Conteúdo informativo. Não constitui recomendação de investimento.**

## 5. Responsabilidades e handoff

Cláudio define direção de arte, composição, tokens, linguagem visual e revisão estética. Codex define arquitetura frontend, integração tipada, implementação, acessibilidade, segurança, desempenho e testes. O responsável humano aprova produto, escopo, dados, política e resultado visual.

Cláudio não inventa dados para completar composição; Codex não altera direção visual aprovada silenciosamente. Segurança, exatidão e acessibilidade são gates comuns.

## 6. Benchmark sem cópia

TradingView e outros terminais são referências de maturidade e interação, nunca templates. Padrões comuns são permitidos: busca, cabeçalho de instrumento, preço, variação, abas, gráfico, watchlist, tabelas e seleção de período. É proibido copiar composição pixel a pixel, identidade, logos, ícones, textos, assets, screenshots, menus ou sequência de telas. A identidade Particle Atlas deve ser original.

## 7. Gramática visual

Malhas/nós representam relações verificáveis entre bolsas, regiões, instrumentos ou eventos. Ondas e contornos representam séries ou densidade documentada. Partículas representam panorama agregado opcional. Camadas empilhadas representam grupos reais separados. Globo técnico é Global Atlas P1 com tabela P0. Espaço negativo preserva hierarquia.

Uma linha de dado corresponde a uma série real. Não duplique uma série para fabricar ondas, relações, partículas, tendências ou previsões. Arte deve desligar sem perda informacional.

## 8. Identidade cromática

Preto, grafite, branco e cinzas neutros ou frios predominam. Dourado, amarelo e âmbar não são identidade, foco, seleção, botão principal, linha padrão, glow ou decoração. Âmbar/laranja só pode indicar status `STALE`/alerta restrito.

Tokens iniciais, sujeitos a WCAG 2.2 AA:

| Token | Valor | Uso |
| --- | --- | --- |
| `--bg-canvas` | `#08090A` | fundo |
| `--bg-panel` | `#111317` | painéis |
| `--bg-elevated` | `#181B20` | elevação |
| `--text-primary` | `#F7F7F5` | texto |
| `--text-secondary` | `#A7ADB6` | metadados |
| `--border-subtle` | `#2A2E35` | grades |
| `--focus-ring` | `#FFFFFF` | foco/seleção com forma |
| `--market-up` | `#4ADE80` | alta |
| `--market-down` | `#F87171` | queda |
| `--market-flat` | `#60A5FA` | estabilidade/referência |
| `--status-stale` | `#FB923C` | status stale restrito |
| `--status-demo` | `#A78BFA` | demo |
| `--status-unavailable` | `#6B7280` | indisponível |

`UP` usa verde + sinal/texto/seta; `DOWN` vermelho + sinal/texto/seta; `FLAT` azul + zero/traço/texto. `FRESH` é neutro e textual. Cor nunca é a única forma de comunicação. Não existe token dourado.

Logos de empresas, fundos, gestoras ou corretoras só podem ser usados com fonte
e licença aprovadas, registradas por origem e finalidade. Até lá, use monograma,
ticker ou placeholder textual.

## 9. Direção e hierarquia dos valores

`PriceDirection = UP | DOWN | FLAT`. `ComparisonBasis = PREVIOUS_CLOSE | RANGE_START | PERIOD_START | COST_BASIS | BENCHMARK`. Cards normalmente usam fechamento anterior; gráfico de período usa início do intervalo; carteira rotula sua base. O frontend não inventa epsilon.

Priorize instrumento, valor real e moeda, variação absoluta, percentual e período/base, fonte, horário, `DataLevel`, `Freshness` e limitação.

Exemplo obrigatório:

```text
VALE3
R$ 150,00 → R$ 220,00
+R$ 70,00 | +46,67%
Índice 100: 100,00 → 146,67
```

`INDEX_100` é escala de comparação, não preço, patrimônio, cota ou saldo.

## 10. Gráfico de série única

Um ativo selecionado produz exatamente uma série financeira principal e uma linha real. A escala padrão mostra valor bruto na unidade/moeda correta, valor inicial/final, variação absoluta/percentual, tooltip com timestamp, moeda, direção, fonte e estado. Gaps permanecem visíveis; efeitos não criam linhas paralelas.

## 11. Comparação com várias séries

Duas ou mais séries exigem duas ou mais séries reais e uma linha por série. O padrão é `INDEX_100`, com primeiro timestamp comparável como base 100; o usuário pode alternar para percentual.

```text
Index100(t) = 100 × Value(t) / Value(base)
ReturnPct(t) = (Value(t) / Value(base) − 1) × 100
```

Use representação Decimal/precisa do domínio. Preço bruto só é habilitado quando moeda, unidade, frequência, calendário, campo econômico e metodologia forem compatíveis. FX aprovado pode criar modo separado, explicitamente identificado. Sem FX, mantenha moedas originais e desabilite comparação absoluta enganosa. Limite recomendado: seis séries desktop e quatro mobile; acima disso, use seleção, pequenos múltiplos ou tabela.

Cada linha possui rótulo direto, símbolo, padrão/traço e estado. Seleção usa espessura/contorno branco. Legenda, rótulos e tabela sincronizam foco, hover e teclado.

## 12. Preço real nunca é escondido

Mesmo em `INDEX_100`, mantenha valor real inicial, focado e final, moeda/unidade, variação absoluta/percentual, base temporal, modo `RAW`, `ADJUSTED` ou `TOTAL_RETURN`, fonte e timestamps no resumo, tooltip, rótulos e tabela acessível. O usuário nunca deve confundir `146,67` com R$ 146,67.

## 13. Séries, carteiras e metodologia

`SeriesKind = MARKET_PRICE | NAV | PORTFOLIO_VALUE | PRICE_RETURN | TOTAL_RETURN | BENCHMARK`; `AdjustmentMode = RAW | ADJUSTED | TOTAL_RETURN`; `NormalizationMode = NONE | PERCENT_CHANGE | INDEX_100`.

Preço de mercado não é NAV; retorno de preço não é retorno total; série ajustada não é preço nominal. Splits, grupamentos, proventos, FX, custo médio e performance precisam de metodologia visível. Aportes/retiradas não parecem lucro; marcadores referenciam eventos reais do ledger; cálculo sem preço/FX aprovado fica `PARTIAL` ou `UNAVAILABLE`.

## 14. Tempo e ausência de dados

Use timestamps reais e timezone explícito. Não faça forward-fill ou interpolação silenciosa em fins de semana, feriados, suspensões ou ausência de provider. Gaps permanecem gaps ou recebem política documentada. O ponto-base precisa existir para todas as séries. Downsampling preserva primeiro, último, mínimos, máximos e eventos relevantes conforme algoritmo testado.

## 15. Contrato frontend–backend para gráficos

OpenAPI é o contrato executável. Tipos devem ser gerados; não invente campos nem duplique schemas. Quando aplicável, o contrato deve sustentar:

```text
ChartSeriesDescriptor: series_id, instrument_id, symbol, label, series_role,
series_kind, exchange, currency, unit, timezone, adjustment_mode, data_level,
freshness, source, source_timestamp, collected_at
ChartPoint: timestamp, actual_value, normalized_value, quality_state
ChartComparisonMetadata: normalization_mode, comparison_basis, base_timestamp,
base_value, fx_policy, missing_data_policy
PerformanceSummary: start_value, end_value, change_absolute, change_percent, direction
```

Valores financeiros atravessam o contrato como string Decimal compatível. `normalized_value` nunca substitui `actual_value`. Se faltar campo, documente lacuna e proponha mudança separada de OpenAPI, migração e testes; não simule no frontend.

## 16. Provenance e estados

Todo número mostra ou torna acessível instrumento, símbolo, bolsa, moeda, unidade, timezone, provider/dataset, horários da fonte/coleta, `DataLevel`, `Freshness`, ajuste, limitações e parcialidade. `DataLevel = REAL_TIME | DELAYED | EOD | DEMO`; `Freshness = FRESH | STALE | UNAVAILABLE`; são dimensões distintas. `DEMO` não concede licença.

Todo componente conectado prevê `initial`, `loading`, `refreshing`, `empty`, erro recuperável/terminal, rate limit, signed-out, forbidden, `FRESH`, `STALE`, `DEMO`, `UNAVAILABLE`, `PARTIAL`, offline, provider outage e feature disabled. Skeleton mantém dimensões; loading não imita valor; stale conserva timestamp; unavailable não vira zero; partial não vira total.

## 17. Camadas do gráfico

Cada gráfico separa verdade (séries, valores, escalas, timestamps e eventos), apresentação (linhas, áreas, grades e tooltip), arte opcional (ondas, contornos e partículas derivadas) e acessibilidade (resumo, tabela e controles HTML). A arte não cria picos, vales, relações, tendência, baseline enganoso, smoothing além dos pontos ou dependência interpretativa.

## 18. Renderização, movimento e desempenho

HTML/CSS/SVG são padrão para UI, gráficos simples, acessibilidade e estados P0
leves. Canvas 2D é recomendado quando densidade, volume de pontos, partículas,
animações ou transições justificarem a escolha, sempre com medição e equivalente
acessível. Não se deve reescrever os gráficos SVG P0 atuais enquanto SVG atender
performance, acessibilidade e fidelidade. `TradingView Lightweight Charts` pode
ser avaliado no futuro, mas nunca é fonte de verdade. WebGL/Three.js permanece
P1, sob feature flag, somente para 3D/Global Atlas avançado.

### Transições e referência Dataism

Dataism é apenas uma referência estética para transições de troca de ativo,
período, refresh completo, navegação e futura revalorização de carteira. Nunca
representa preço, tick, dado, previsão ou volatilidade; não roda a cada tick, não
bloqueia a leitura do número e deve ser desligado ou reduzido com
`prefers-reduced-motion`.

Movimento comunica atualização/seleção/transição, não decoração permanente. Respeite `prefers-reduced-motion`, permita pausar/parar/ocultar atualização contínua, suspenda fora da viewport/documento oculto e degrade arte antes da linha financeira. Meça LCP, INP, CLS, bundle, frame time e cold load no ambiente real.

## 19. Responsividade

Valide 320, 375, 768, 1024 e 1440 px, orientação paisagem, português e zoom de 200%. Mobile prioriza valor real, variação, período, gráfico, fonte e estado; limita comparação visual a quatro séries e mantém tabela completa. Nenhum dado crítico desaparece silenciosamente.

## 20. Acessibilidade

WCAG 2.2 AA é gate mínimo: HTML semântico, teclado, foco branco visível, contraste de linhas/textos, alvos adequados, labels acessíveis, tabela/resumo equivalente, tooltip por teclado/toque, sem depender de cor/hover/animação e reduced motion preservando informação. Axe não substitui revisão manual.

## 21. Segurança e privacidade

Sessão opaca usa cookie `HttpOnly`; nunca browser storage. Não exponha provider key, cron secret ou configuração interna. Mutações seguem CSRF/Origin; autorização de carteira é backend; conteúdo rico é sanitizado; logs/analytics não recebem PII ou eventos desnecessários; erros não revelam stack, SQL ou payload sensível.

## 22. Arquitetura de componentes

Separe obtenção/cache, cliente OpenAPI gerado, view model, formatação, chart core, escalas/normalização, layers de séries/eventos/arte, interação/hit testing, acessibilidade e telemetria. Evite `any`, componente monolítico e cálculo financeiro no desenho.

## 23. Testes obrigatórios

Cubra matemática de `INDEX_100`, percentuais, UP/DOWN/FLAT, moedas/FX, RAW/ADJUSTED/TOTAL_RETURN, gaps/calendários, Decimal, contrato OpenAPI, uma série/uma linha, N séries/N linhas, valores reais simultâneos, cores/padrões/labels/tabela, estados, breakpoints, zoom, teclado, reduced motion, resize/DPR, cleanup, offscreen e arte desligável.

## 24. P0, P1 e cortes

P0: identidade preto/branco/cinza; shell, dashboard, busca, página de ativo, gráfico de série única, comparação multissérie `INDEX_100` com valores reais, watchlist, carteiras e performance informativas, provenance, estados, responsividade, acessibilidade, heatmap básico e tabelas equivalentes.

P1: fundos tradicionais condicionados a licença/cobertura, partículas, topografias, malha Global Atlas, globo 3D, comparações acima dos limites e transições sofisticadas. Ao ameaçar prazo, corte P1 primeiro; nunca corte exatidão, preço real, provenance, licença, segurança, acessibilidade ou testes financeiros.

## 25. Anti-patterns bloqueados

Dourado como identidade/foco; azul como foco quando significa `FLAT`; série multiplicada em ondas falsas; preço bruto incompatível; índice como preço; preço real escondido; gaps preenchidos; smoothing/extrapolação; gráfico sem tabela; cor sem texto/padrão; Canvas sem fallback; WebGL no P0; mock como real; endpoint/campo inventado; cálculo financeiro no componente; cópia de concorrente; efeito sem significado/orçamento.

## 26. Definição de pronto

Fontes lidas; série, base, moeda, unidade e metodologia explícitas; valores reais visíveis; uma série não gera linhas falsas; comparação honesta/testada; cores UP/DOWN/FLAT não exclusivas; sem dourado como identidade; provenance/estados corretos; desktop/tablet/mobile/zoom/reduced motion verificados; segurança, privacidade, testes, contrato, acessibilidade, regressão e desempenho verdes; Cláudio e responsável humano aprovaram; diff sem escopo incidental.

## 27. Manutenção

Mudança normativa exige decisão humana explícita. Não altere silenciosamente durante feature. Decisões arquiteturais recebem ADR de sucessão. Regras mecânicas devem ser reforçadas por tipos, testes e CI. Em divergência, comportamento seguro, informativo e rastreável prevalece.
