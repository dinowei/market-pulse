# ADR-031: Visual Obsidian Glass

- **Status:** Accepted (decisão do responsável, 2026-11-05)
- **Substitui:** a identidade visual da ADR-028; o workspace de gráficos continua.

## Contexto

O responsável pediu o site com o visual da imagem de referência (vidro fosco, barra flutuante, abas em pílula, fotos), trocando só o fundo dourado por cinza. As telas foram geradas no Stitch e usadas como referência.

## Decisão

- Tokens neutros de grafite; verde, vermelho e azul seguem reservados a alta, queda e estabilidade.
- Barra flutuante de ícones para a área pessoal e abas em pílula para o mercado; todas as seções continuam acessíveis.
- Início e a nova rota `/regions` consomem `/api/v1/market-data/world-report`.
- Fonte Plus Jakarta Sans, auto-hospedada.
- As fotos em `public/market/` são geradas pelo Stitch e provisórias, até o responsável fornecer as definitivas.

## Fora da implementação

O que as telas do Stitch inventavam e o backend não tem ficou de fora: podcast, "Compra Forte", latência, login com Google e Apple, 2FA e a barra falsa de navegador.

Carteiras, Favoritos, Calendário, Ativo e Conta herdam o novo visual, mas mantêm a disposição e as funções atuais; o layout das telas do Stitch não foi copiado nelas.

## Consequências

`backdrop-filter` só na janela principal, por custo em máquinas modestas. Medidas: testes unitários, axe e orçamento de bundle.
