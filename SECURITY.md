# Política de segurança

## Reporte

Não publique vulnerabilidade, credencial ou dado pessoal em issue. Use um canal privado do mantenedor; o canal definitivo está pendente e deve ser registrado antes de exposição pública. Até lá, interrompa a publicação e contate diretamente o operador do repositório por meio privado previamente acordado.

Inclua impacto, reprodução mínima, versões afetadas e evidência sanitizada. Não inclua token, cookie, senha, dump ou dado de terceiro.

## Severidade inicial

- **Crítica:** execução remota, bypass amplo de autenticação, segredo de produção ou perda massiva.
- **Alta:** acesso indevido relevante, escalada ou exposição limitada de dados sensíveis.
- **Média:** controle contornável com pré-condições ou impacto limitado.
- **Baixa:** hardening, informação não sensível ou impacto improvável.

## Credencial exposta

1. Revogar/rotacionar fora do repositório.
2. Suspender deploy/integração afetada.
3. Preservar evidência sem republicar o valor.
4. Investigar logs e alcance.
5. Remover do histórico somente com plano aprovado; apagar arquivo atual não basta.
6. Registrar causa e prevenção.

## Dados sensíveis

Solicitações de correção/remoção devem usar canal privado e comprovar autoridade. Não copie dados sensíveis para issues ou fixtures.

## Fora do processo inicial

Não há bug bounty, SLA de resposta, pentest contratado, contato público dedicado ou processo regulatório formal no Dia 1. Esses itens são pendências antes do lançamento público.
