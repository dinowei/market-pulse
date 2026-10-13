# Matriz das referências visuais do Dia 41

- Data: 2026-10-11
- Origem: seis imagens enviadas pelo usuário como referência de design, sem autoria nem
  licença informadas. São usadas só como referência de estrutura e experiência
  ([diretriz §6](PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md)). Nenhuma imagem, texto, marca,
  ícone ou composição foi copiado para o repositório.
- Código comparado: `feature/dia-41-sync` em `4916e5b`.

## Leitura de cada imagem

| # | Imagem | Elementos e hierarquia | Tipografia e cor | O que é dado e o que é decoração |
| --- | --- | --- | --- | --- |
| R1 | Pôster: faixa ondulada feita de partículas brancas, em diagonal, com colunas de microtexto nas laterais | Uma forma central domina; texto pequeno nas margens; muito espaço negativo | Microtexto monoespaçado; grafite, branco e cinza | Decoração: a faixa não representa série nenhuma. O microtexto imita dados, sem fonte |
| R2 | Muitas linhas brancas finas sobrepostas, como traços de osciloscópio | Sem eixos nem rótulos; densidade cria a forma | Sem texto; branco sobre preto, traço fino | Ou são N séries reais (comparação), ou uma série duplicada, o que a diretriz §7 proíbe |
| R3 | Painel técnico: superfícies em malha empilhadas numa caixa 3D, três miniaturas laterais e legendas em gradiente | Título fino no topo; figura principal à esquerda; miniaturas e legendas à direita | Branco, bege e gradiente até vermelho para intensidade | Representa dados de simulação; aqui seria camadas de grupos reais. O gradiente para vermelho choca com a regra de vermelho = queda |
| R4 | Terminal: "montanha" de partículas (densidade), números grandes, tabelas laterais, segundo gráfico de partículas e histogramas com grade pontilhada | Leitura numérica grande no topo, gráfico central, tabelas à direita, histogramas embaixo | Monoespaçada; branco e cinza sobre preto | Os números e histogramas seriam dados; a montanha exige uma distribuição real (ex.: histograma de retornos) |
| R5 | Pôster: vórtice de malha e partículas dentro de uma moldura retangular de linhas finas, com grade de pontos nos cantos | Figura central emoldurada; textos de canto pequenos | Microtexto; preto, branco e leve iridescência | Decoração pura |
| R6 | Painel de terceiros: globo 3D pontilhado ao centro, arcos de fluxo, KPIs, gráficos pequenos, tabela e calendário de pontos | Cabeçalho com título; colunas laterais de cartões; globo dominante; legenda de chips no rodapé | Monoespaçada e CJK; preto com laranja nos destaques | Os KPIs e arcos seriam dados de terceiros; a identidade, os textos e a composição pertencem a outra marca e **não** podem ser copiados |

Comportamento esperado nas seis: leitura escura, densa e técnica, com o dado em
destaque e a decoração em segundo plano. Nenhuma traz informação de acessibilidade;
todas dependem de cor fina sobre preto, o que exige conferir contraste caso a caso.

## Matriz elemento × código

Classificação: igual, parcialmente igual, ausente, visualmente diferente, funcionalmente
diferente, não implementável sem provider, não implementável sem decisão, apenas
referência visual, incompatível com o escopo atual.

| Elemento (imagem) | Existe no código? | Onde | Diferença | Classe | P0/P1/conceito | Ação |
| --- | --- | --- | --- | --- | --- | --- |
| Fundo escuro com espaço negativo (todas) | Sim | Tokens `--pa-bg-*`, tema escuro | — | Igual | P0 | Nenhuma |
| Microtexto monoespaçado em colunas (R1, R4, R5, R6) | Parcial | Rótulos `.eyebrow` em caixa alta; monoespaçada só em ids de requisição | Família da fonte | Não implementável sem decisão | P0 (tipografia) | Registrar: trocar a família é decisão de identidade (Cláudio e o responsável) |
| Números alinhados em colunas (R4, R6) | Parcial | `tabular-nums` em preço, carteira e hub | Tabelas comuns ainda sem algarismos tabulares | Parcialmente igual | P0 | **Implementar**: algarismos tabulares em todas as tabelas |
| Leitura numérica grande (R4) | Sim | `.asset-price` (2rem) na página de ativo e no dashboard | — | Igual | P0 | Nenhuma |
| Grade pontilhada no gráfico (R4) | Não | `particle-chart.tsx` só tem o eixo | Sem linhas de referência | Ausente | P0 (apresentação) | **Implementar**: três linhas pontilhadas horizontais, sem valor inventado |
| Histogramas na base (R4) | Parcial | Volume nos candles (ADR-023) | Só quando o provider manda volume | Parcialmente igual | P0/P1 | Nenhuma; outros histogramas exigem dado |
| Montanha de partículas = distribuição (R4) | Não | — | Exige distribuição real | Não implementável sem provider | Conceito | Registrar |
| Faixa ou superfície de partículas (R1, R5) | Não | — | Seria arte sem série | Apenas referência visual | P1 | Não implementar como dado; ver a linha do traçado |
| Pontos que acompanham a linha ao desenhar (R1, R4) | Parcial | Pontos `chart-point` aparecem juntos após o traço | Sem sequência | Visualmente diferente | P1 (movimento) | **Implementar**: pontos surgem em sequência durante o traço, uma vez, desligável |
| Muitas linhas sobrepostas (R2) | Sim, com N séries reais | `/compare` (até 10 séries, INDEX_100) | Traço mais grosso, sem camadas de opacidade | Parcialmente igual | P0 | Nenhuma; duplicar série é proibido (§7) |
| Camadas empilhadas em 3D (R3) | Não | — | WebGL e grupos reais em camadas | Não implementável sem decisão | P1 (WebGL, §18) | Registrar |
| Legenda em gradiente até vermelho (R3) | Não | — | Vermelho é reservado a queda | Incompatível com o escopo atual | — | Não implementar |
| Miniaturas laterais (R3) | Parcial | Cartões da visão geral de `/markets`, heatmap | — | Parcialmente igual | P0 | Nenhuma |
| Moldura de linhas finas (R5) | Parcial | Bordas `hairline`; borda tracejada do gráfico | Uma linha só | Parcialmente igual | P1 | Nenhuma |
| Grade de pontos de fundo (R5, R6) | Não | — | Textura | Apenas referência visual | P1 (arte) | **Implementar** só no pulso de `/markets` (já desligável), em token de borda |
| Globo 3D pontilhado (R6) | Não | Global Atlas em tabela (ADR-019) | Globo é P1 com WebGL | Não implementável sem decisão | P1 | Registrar (ADR-019 e §18) |
| Arcos de fluxo entre regiões (R6) | Não | — | Exigem relações verificáveis entre bolsas | Não implementável sem provider | Conceito | Registrar |
| KPIs no topo (R6) | Parcial | Contagens reais na visão geral de `/markets` | Sem KPIs de mercado | Funcionalmente diferente | P0 | Nenhuma; KPI de mercado exige fonte |
| Calendário de pontos (R6) | Parcial | `/calendar` em tabela | Formato | Visualmente diferente | P1 | Nenhuma |
| Destaques em laranja (R6) | Não | Âmbar só para `STALE` | — | Incompatível com o escopo atual | — | Não implementar |
| Cabeçalho e menu (R6) | Sim | `.topbar` com navegação | Composição de terceiros | Igual na função | P0 | Nenhuma |
| Chips de legenda no rodapé (R6) | Parcial | Barra de status no rodapé | — | Parcialmente igual | P0 | Nenhuma |

## Implementado a partir desta matriz

As quatro ações marcadas como **Implementar**:

- algarismos tabulares nas tabelas;
- grade pontilhada do gráfico;
- pontos em sequência durante o traço;
- grade de pontos no pulso de `/markets`.

Todas são de apresentação ou movimento P1. Não criam série, valor nem relação, desligam
com `NEXT_PUBLIC_ATLAS_MOTION=off` ou com movimento reduzido quando são movimento, e têm
teste.

## Decisões pedidas ao responsável

1. **Tipografia de dados:** usar fonte monoespaçada em rótulos e números, como nas
   referências, muda a identidade e o design system. Fica para Cláudio e o responsável.
2. **Globo 3D, camadas empilhadas e superfícies de partículas:** P1 com WebGL (§18). Exige
   ADR, medição de desempenho e equivalente acessível.
3. **Distribuições, arcos de fluxo e KPIs de mercado:** exigem provider aprovado na
   [matriz de licenças](../DATA_PROVIDER_LICENSE_MATRIX.md).

## Revisão sobre o staging publicado (2026-10-11)

Revisão feita no staging (`c3e77c0` na Vercel) em 1280 px e 375 px, nos temas claro e
escuro. Corrigi só o que a matriz justifica: hierarquia, microtexto e responsividade.

| Elemento | Estado antes | Alteração | Estado depois | Teste |
| --- | --- | --- | --- | --- |
| Algarismos nas tabelas (R4) | Proporcionais fora de preço e carteira | `tabular-nums` em `table` | Colunas alinhadas | E2E axe e reflow (`day36-wcag.spec.ts`) |
| Grade do gráfico (R4) | Só o eixo | Três linhas pontilhadas, sem rótulo | Referência visual, nenhum valor novo | `day41-chart-type.test.ts` (3 linhas, nenhum `<text>`, uma série = uma linha) |
| Pontos durante o traço (R1, R4) | Surgiam juntos depois do traço | `--d` por ponto, na ordem da série | Pontos acompanham a linha, uma vez | `day41-chart-type.test.ts` (ordem 0 → 1) e E2E "motion stops" |
| Textura do pulso (R5, R6) | Gradiente liso | Grade de pontos em token de borda | Desliga com a arte | Revisão visual; E2E axe |
| Rótulos do pulso (R1, R5: microtexto) | Texto no SVG, escalado com o desenho (~21 px a 1280 px) e alternado em duas linhas | Rótulos em HTML, uma coluna por família, `.66rem` em caixa alta, com a contagem | Tamanho fixo e alinhado a cada família | `day41-markets.test.ts` (sem `<text>` no SVG, uma coluna por família) |
| Botão "Sair" do menu (R6: cabeçalho) | Estilo padrão do navegador, maior que os links | Mesmo estilo dos links do menu | Menu uniforme | E2E teclado e axe |
| Cabeçalho no celular (R6) | A regra móvel mirava `.search` (o `label`), não o item da grade; busca espremida e botões no meio | Marca, busca em largura total, botões e menu, nessa ordem | Ordem de leitura | E2E reflow em 320, 375 e 640 px |

### Diferença que não é de design

No staging publicado, o pulso mostrava "7 estáveis" e o catálogo tinha 5 itens. A causa é
a API do Render ainda em `1747184`, com o FLAT inventado já corrigido em `6879f37`. O
problema some com o deploy da API, sem mudança visual.

## Dados e providers (ADR-025)

Elementos das referências que só podem existir com dado real. Até um provider passar no
gate de licença, todos aparecem como indisponíveis, com o motivo, ou ficam fora da tela.

| Elemento da imagem | Existe? | Local no código | Diferença | Dados necessários | Provider necessário | Ação |
| --- | --- | --- | --- | --- | --- | --- |
| Leitura numérica grande (R4) | Sim | `.asset-price` | Valor DEMO no staging | Cotação com horário | brapi (BR) ou Massive (EUA), aprovados | Esperar a ativação |
| Histogramas de volume (R4) | Sim, nos candles | `particle-chart.tsx` | Só com volume completo | Volume por barra | Twelve Data, Massive ou brapi | Esperar a ativação |
| Muitas séries sobrepostas (R2) | Sim | `/compare` | Benchmarks sintéticos | Séries reais por instrumento | Um provider por série, sem costura | Esperar a ativação |
| Montanha de partículas, distribuição (R4) | Não | — | — | Distribuição de retornos com fonte | Qualquer provider de histórico aprovado | Plano técnico depois da ativação |
| Arcos de fluxo e globo (R6) | Não | Atlas em tabela | P1 | Relações verificáveis entre bolsas | Nenhum dos sete fornece | Fora do escopo atual |
| KPIs de mercado (R6) | Não | Visão geral de `/markets` com contagens | Sem KPI de mercado | Altas, quedas e volume do pregão | Exige licença de exibição | Fora até haver licença |
| Câmbio ao vivo (R6) | Parcial | Aba Câmbio, sintética | Sem fonte | USD/BRL com horário | Open Exchange Rates (horária) | Primeiro candidato da revisão de licença |
