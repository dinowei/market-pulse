# ADR-030: Relatório mundial de fechamento como página inicial

- Status: Accepted
- Data: 2026-11-05
- Decisores: responsável humano pelo produto (uso pessoal de estudo; "pode construir");
  implementação por Claude Code
- Relação: amplia a [ADR-027](027-owner-private-real-data-staging.md) e a
  [ADR-029](029-owner-real-data-universe.md); não altera o fluxo editorial do Morning Call.

## Decisão

1. A página inicial mostra um quadrado por região: Brasil, América do Sul, Estados Unidos,
   América do Norte, Europa, Ásia e Oceania, moedas e cripto. O painel anterior vai para
   `/terminal`; nenhum dado ou ferramenta é removido.
2. **Medida:** ETFs listados nos EUA, em dólar, sempre rotulados. Não são o índice local nem
   seus pontos. Sem ETF único, média simples declarada; moedas não têm média.
3. **Texto automático por regra, sem IA:** descreve o movimento e os extremos dos ativos
   acompanhados. Fica fora do Morning Call editorial, que segue com revisão humana.
4. **Causa:** o sistema não afirma por que um mercado subiu ou caiu. Manchetes da Massive
   aparecem ao lado, com fonte, só na sessão do responsável.
5. **Falta de dado:** nunca vira zero; o quadrado mostra o motivo.

## Consequências

- Os títulos das notícias vêm em inglês, e a cobertura fora dos EUA não foi medida.
- Risco de licença igual ao da ADR-027 (H-34), agora também para manchetes.
- Em cache frio, as cotas por minuto deixam parte dos ativos "sem dado agora" até a próxima
  janela.
- Pendentes: demais telas no visual de vidro e imagens dos quadrados.
