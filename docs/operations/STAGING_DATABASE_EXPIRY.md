# Banco do staging: expiração em 2026-11-05

- **Data:** 2026-10-11 (UTC). **Decisão pendente do usuário (H-29).**
- **Fato medido:** a instância `market-pulse-staging-db` (Postgres 16, plano grátis do
  Render, região Oregon) informa `expiresAt = 2026-11-05T02:59:10Z` na API do Render,
  consultada em 2026-10-10.
- **Não verificado aqui:** o que o Render faz com os dados depois da expiração e os preços
  dos planos pagos. Confira na documentação e na página de preços oficiais antes de decidir.
- **Este documento não autoriza** contratação, mudança de painel nem deploy.

## O que está em jogo

O staging guarda uma conta, as watchlists e as carteiras de teste do responsável, além das
migrations aplicadas. Não há dado de cliente. A perda é recuperável, mas o staging fica fora
do ar até haver um banco novo.

## Opções

| Opção | O que é | Custo | Risco |
| --- | --- | --- | --- |
| A. Plano pago do Render | Manter a mesma instância e região | Mensal (confirmar no Render) | Baixo; nada muda no código |
| B. Branch `production` do Neon | O que o NotebookLM previa (PDF de infraestrutura): Postgres 16 gerenciado em São Paulo | Plano grátis do Neon (confirmar limites) | **Latência:** a API fica em Oregon e o banco em São Paulo; cada consulta cruza o continente. Medir antes de adotar |
| C. Recriar um banco grátis no Render | Deixar expirar e criar outro pelo Blueprint | Zero | Repete a cada ciclo do plano grátis; conta e listas recriadas à mão |

**Recomendação:** para um staging privado de uma pessoa, **C** é suficiente agora, e
**A** se a interrupção mensal incomodar. **B** só depois de medir a latência entre Oregon
e São Paulo, ou com a API movida para mais perto do banco.

## Passos por opção (para o usuário executar)

**A.** No painel do Render, na instância `market-pulse-staging-db`, mudar o plano antes de
2026-11-05. Nada muda no repositório.

**B.**

1. No console do Neon, criar a string de conexão da branch `production`, com conexão
   direta (sem `-pooler`) e `sslmode=require`.
2. No `render.yaml`, trocar `MARKET_PULSE_DATABASE_URL` de `fromDatabase` para
   `sync: false` (mudança de código, com revisão) e colar a string **só no painel** do
   Render.
3. Fazer o deploy: o comando de start aplica as migrations no banco novo.
4. Recriar a conta abrindo o cadastro por alguns minutos
   (`MARKET_PULSE_REGISTRATION_ENABLED=true`, depois `false`), como no Dia 29.
5. Medir `/health/ready` e os tempos do Dia 38, e comparar com os de hoje.

**C.**

1. Antes de 2026-11-05, exportar os dados da conta pela página `/account` (Exportar meus
   dados), se quiser guardar uma cópia.
2. Depois da expiração, sincronizar o Blueprint para recriar o banco.
3. Recriar a conta como no passo 4 da opção B.

Em qualquer opção, nunca colar credenciais em chat, documento ou commit.
