# ADR-032: Menos páginas, mapa 3D e leitura em lote dos provedores

- **Status:** Accepted (decisão do responsável, 2026-11-05)
- **Atualiza:** ADR-019 (heatmap básico), ADR-023 (hub de mercados), ADR-030 (relatório mundial)

## Contexto

O responsável pediu menos páginas, sem perder informação, um heatmap igual ao de referência, em perspectiva e com ativos reais, e o melhor uso de cada dado recebido das chaves de API. As cotações eram pedidas uma a uma, o que esgotava as cotas por minuto, e `/compare` e `/heatmap` chamavam a API sem a sessão, recebendo sempre indisponível.

Medido em 2026-11-05 com as chaves do responsável: `brapi /quote/list` traz numa chamada preço, variação, volume, valor de mercado e setor de 2.000 ativos; `massive /v2/aggs/grouped` traz um dia inteiro de 12.606 tickers (o dia corrente responde 403); a brapi dá 3 meses de histórico a qualquer ativo da B3 e recusa 1 ano à maioria.

## Decisão

- **Páginas:** `/regions`, `/terminal` e `/markets` saem, com redirecionamento. Região abre no próprio Início; gráfico, Morning Call e panorama ficam no Início, carregados ao rolar; a tabela por família fica em `/atlas`, com o catálogo.
- **Lote:** listas (relatório mundial, tabela de ativos, heatmap) leem um instantâneo por mercado e só caem para a chamada por ativo quando ele não cobre. A página do ativo mantém a cotação mais recente.
- **`/market-data/market-map`:** B3 com setor e valor de mercado da fonte; EUA com o pregão fechado, área pelo valor negociado e setor classificado por este projeto, e a tela diz isso.
- **`/market-data/profile/{id}`:** todos os fatos das fontes sobre o ativo, com a fonte de cada um, cacheados por 12 horas.
- **Heatmap:** CSS 3D, sem biblioteca nova; tabela equivalente, controles por teclado e modo plano.
- **Comparar:** fica, porque há histórico real. Base 100 na primeira data comum entre as séries, porque as fontes têm profundidades diferentes.
- **Notícias:** artigo de terceiro com chamada de compra ou venda é descartado pelo filtro `_RECOMMENDATION`.
- **Fluidez:** cache em memória com revalidação em segundo plano, limpo no login e no logout; GZip nas respostas da API.

## Consequências

- Áreas repetem o valor da empresa em ações de classes diferentes (PETR3 e PETR4); a tela declara.
- O filtro de notícias é por palavras: pode descartar notícia inofensiva e deixar passar outra. Não substitui revisão humana (H-13).
- Dados dos EUA nas listas são do último pregão fechado, marcados como EOD.
- A licença pública das fontes segue sem revisão (H-34): tudo continua restrito à sessão do responsável.
