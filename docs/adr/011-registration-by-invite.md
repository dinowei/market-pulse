# ADR-011: Cadastro por convite de uso único

- Status: Accepted
- Data: 2026-10-05
- Decisores: responsável técnico (Claude Code), com delegação explícita do operador do
  projeto para a "decisão sobre convite" do Dia 30
- Relação: completa o H-11 ([DAY29_HANDOFF.md](../DAY29_HANDOFF.md)). O fechamento por
  padrão em `staging`/`production` já existe desde o Dia 29 (`registration_open`).

## Contexto

`POST /api/v1/auth/register` só aceita cadastro aberto ou fechado. Para abrir o produto a
outras pessoas é preciso controlar quem entra, sem infraestrutura de e-mail: envio e
verificação de e-mail estão fora do escopo ([PROJECT_SPEC.md](../PROJECT_SPEC.md),
[AUTH_SESSIONS_DAY_18.md](../security/AUTH_SESSIONS_DAY_18.md)). Uma allowlist de e-mails
em variável de ambiente colocaria dado pessoal em configuração e exigiria redeploy a cada
pessoa.

## Decisão

Três modos de cadastro, com padrão seguro por ambiente:

| Modo | Uso | Padrão |
|---|---|---|
| `OPEN` | `local` e `test` | sim, nesses ambientes |
| `CLOSED` | staging privado de 1 usuário | sim, em `staging`/`production` |
| `INVITE` | abertura do produto a outras pessoas | só por configuração explícita |

No modo `INVITE`:

- Um `ADMIN` gera o convite por **comando administrativo interno**, como o Morning Call
  (sem endpoint público de emissão). O código tem 256 bits aleatórios, é exibido **uma
  única vez** e entregue fora da aplicação.
- O banco guarda apenas o **hash SHA-256** do código, mais emissor, criação, expiração
  (padrão 72 h), uso e usuário criado. Nunca guarda o código nem o e-mail do convidado.
- O cadastro consome o convite e cria o usuário na **mesma transação**, com
  `UPDATE ... WHERE used_at IS NULL AND expires_at > now() RETURNING`. Isso impede uso
  duplo em corrida, e convite inválido, expirado ou usado devolve a mesma resposta
  genérica.
- Emissão e consumo geram linha em `audit_logs` sem o código e sem o e-mail.
- O rate limit de autenticação (5/60 s) continua valendo para tentativas de convite.

## Alternativas consideradas

- **Allowlist de e-mails por variável de ambiente:** dado pessoal em configuração e
  redeploy por pessoa. Rejeitada.
- **Verificação de e-mail:** exige provedor de e-mail, fora do escopo do beta.
- **Cadastro aberto com mitigação:** incompatível com o beta controlado.

## Consequências

- Contrato: `RegisterRequest` ganha `invite_code` opcional (OpenAPI e cliente gerado
  atualizados, sem editar o cliente à mão); o formulário de cadastro ganha o campo quando
  o modo for `INVITE`.
- Nova tabela `registration_invites` por migration Alembic reversível.
- **Implementação:** obrigatória antes de abrir o produto. Sugestão: Dia 39, junto dos
  demais itens de abertura; o staging privado continua em `CLOSED`.

## Como revisar esta decisão

Revisar se o produto adotar envio de e-mail ou login social.
