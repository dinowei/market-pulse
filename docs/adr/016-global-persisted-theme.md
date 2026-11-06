# ADR-016: Tema global e persistido; decisões sobre os achados da ADR-015

- Status: Accepted
- Data: 2026-10-07
- Decisores: responsável humano pelo produto (decisões abaixo); implementação por Claude Code
- Relação: resolve os achados da [ADR-015](015-oklch-tokens-and-theme-contrast.md) sem
  alterá-la

## Decisões do usuário (2026-10-07)

1. **Tema global, persistido no navegador.**
2. **Âmbar de importância média no calendário: mantido como está.** O desvio da regra
   "âmbar só para `STALE`/alerta restrito" (diretriz §8) fica aceito e registrado para o
   calendário econômico do Dia 26. A importância continua também em texto, então a cor
   não é a única pista.
3. **Downsampling da comparação multissérie: Dia 35 em diante.**

## Implementação do tema

- O tema fica em `<html data-theme>` e vale para todas as páginas. As páginas deixaram de
  fixar `data-theme="dark"`.
- **Ordem de resolução:** escolha salva → `prefers-color-scheme` do sistema → escuro.
- **Sem "flash":** um script inline (`next/script`, `strategy="beforeInteractive"`, no
  layout raiz, conforme a documentação do Next 16 instalada) aplica o tema antes da
  hidratação; `<html>` usa `suppressHydrationWarning`.
- **Armazenamento:** só a chave `market-pulse.theme` com `"dark"` ou `"light"`. Não é
  sessão, token nem dado pessoal; a diretriz §21 ("sessão opaca nunca em browser storage")
  continua atendida. Se o armazenamento estiver bloqueado, o tema vale só naquela visita.
- O botão continua no cabeçalho do dashboard e usa `useSyncExternalStore`, sem estado
  duplicado.

## Consequências e pendências

- **CSP do frontend (H-02):** o script inline precisará de hash ou nonce quando a CSP for
  adotada. Ele é estático (`THEME_INIT_SCRIPT`), então o hash é estável.
- O botão de tema só existe no dashboard; levá-lo às demais páginas é decisão de layout.

## Evidência

`apps/web/app/theme-global.test.ts`: regra de resolução; o script inline executado em
sandbox (escolha salva, sistema, valor inválido, armazenamento bloqueado → escuro);
layout com o script antes da hidratação; nenhuma página fixa tema; só o módulo de tema
grava no armazenamento. O build confirmou o script no HTML gerado.
