# ADR-013: Downsampling de exibição de séries históricas (M4, opt-in)

- Status: Accepted
- Data: 2026-10-07
- Decisores: responsável técnico (Claude Code), com autorização explícita do operador para
  executar o Dia 31 da Fase 2
- Relação: atende à diretriz Particle Atlas, §14 ("Downsampling preserva primeiro, último,
  mínimos, máximos e eventos relevantes conforme algoritmo testado"), e às "Regras
  anti-distorção" da semântica de gráficos

## Contexto

As janelas `5A` e `MAX` chegam a ~1.250 e ~2.500 pregões diários. Desenhar todos os pontos
no SVG P0 não acrescenta informação visível numa largura de ~800 px e aumenta o peso da
resposta e do DOM. Qualquer redução, porém, não pode criar, mover, arredondar ou suavizar
pontos, esconder gaps ou sumir com picos e quedas.

## Decisão

1. **Algoritmo M4 por faixas de índice** (`app/market_data/downsampling.py`): a série é
   dividida em `max_points // 4` faixas; de cada faixa ficam o primeiro, o último, o
   mínimo e o máximo do valor exibido (`value`, ou `close` quando `value` falta). Todo
   ponto com `is_gap` ou sem valor é **sempre** mantido. Empates escolhem o índice mais
   antigo, o que torna o resultado determinístico.
2. **Saída é subconjunto exato e ordenado** dos pontos originais. Valores `Decimal`,
   timestamps, OHLC e `index_100` dos pontos mantidos não são recalculados. O
   `index_100` continua com base no primeiro ponto da série completa, que é sempre
   preservado.
3. **Opt-in e declarado.** `GET /api/v1/market-data/history/{id}` aceita `max_points`
   (64–5.000). Sem o parâmetro, a série completa volta como antes. Quando há redução, a
   resposta traz `downsampling` (método, limite, pontos originais e retornados, o que foi
   preservado e a base do cálculo). O frontend pede 500 pontos para o gráfico principal e
   mostra um aviso com a contagem; a legenda da tabela também informa a redução.
4. **M4 em vez de LTTB:** o LTTB escolhe pontos por área de triângulo e não garante que
   mínimos e máximos de cada faixa sobrevivam; o M4 garante por construção.

## Fora de escopo, registrado

- **Comparação multissérie (`/market-data/history/batch`) não é reduzida.** Reduzir cada
  série de forma independente desalinharia os timestamps entre séries em `INDEX_100`.
  Exige uma decisão própria, com faixas comuns de tempo.
- **Extremos intradiários** (`high`/`low` da barra) não guiam a escolha; a série exibida é
  de fechamento. Os OHLC dos pontos mantidos permanecem intactos.
- A DEMO atual tem cerca de 440 pregões, abaixo do limite de 500; a redução aparece com
  provider real ou séries longas.

## Consequências

- **Positivas:** resposta e SVG limitados; extremos, gaps e trajetória preservados; o
  usuário é informado; contrato aditivo (campo e parâmetro opcionais).
- **Negativas:** a tabela fallback da tela mostra a série reduzida, declarada. A série
  completa continua disponível pela API sem `max_points`.

## Evidência

`tests/test_downsampling_day31.py`: subconjunto exato e ordenado, limite de tamanho,
primeiro, último, pico isolado, fundo de queda em V e extremos de cada faixa preservados,
gaps preservados, `index_100`/`Decimal` intactos, determinismo, validação de `max_points`
e endpoint (sem parâmetro igual a antes; com parâmetro, redução declarada; 422 fora da
faixa). No web, `app/downsampling-day31.test.ts`.
