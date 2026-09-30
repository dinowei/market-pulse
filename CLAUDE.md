# Market Pulse

@AGENTS.md

As instruções operacionais completas estão em `AGENTS.md`, importado acima, e as
regras complementares de documentação em [docs/CLAUDE.md](docs/CLAUDE.md).

## Estado atual

Somente fatos verificados. Não promova hipótese a decisão nesta seção.

- **Dias 24 a 27: fechados.** Demonstração local persistida e isolada, painel
  operacional interno, comparação multiativo, calendário econômico, proventos,
  marcadores e telemetria Web Vitals.
- **Dia 28: PARTIAL.** Implementado e commitado na branch
  `feature/dia-28-hardening`, com validação final pendente.
  - A suíte completa **não foi executada** na sessão de fechamento, por limite de
    memória da máquina.
  - O CI do repositório está em `startup_failure`, condição anterior a esta
    branch, portanto **não há evidência automatizada**.
  - Os commits `0c166c9` (expurgo de registros operacionais) e `d85cd63` (teste
    de vazamento de credencial em log) **não foram validados**: o código existe,
    os testes existem, nenhum dos dois rodou.

O Dia 28 só pode ser declarado concluído depois que a suíte completa rodar verde
e a evidência for registrada. Pendências detalhadas em
[PRODUCTION_RUNBOOK_DAY_28.md](docs/operations/PRODUCTION_RUNBOOK_DAY_28.md).
