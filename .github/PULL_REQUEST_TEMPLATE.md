# Resumo e autorização

- Dia/subtarefa autorizada:
- Objetivo:
- Fora do escopo preservado:

## Arquivos e decisões

- Arquivos alterados:
- ADR/política/spec afetada:
- Justificativa para qualquer decisão material:

## Evidências

Liste comandos, versões relevantes, resultados e exit codes. Não marque verificação indisponível como aprovada.

- Build:
- Lint:
- Typecheck:
- Testes unitários/integração/E2E:
- Verificação manual/a11y:
- Migração/rollback:

## Checklist obrigatório

### Escopo e qualidade

- [ ] A mudança pertence somente ao dia/subtarefa autorizada.
- [ ] Dependências do roadmap e critérios de aceite foram satisfeitos.
- [ ] Diff completo e arquivos staged foram revisados.
- [ ] Testes relevantes foram adicionados/executados; ausências estão justificadas.
- [ ] Documentação e OpenAPI foram atualizadas quando aplicável.
- [ ] Mudança material respeita ADR aceita ou inclui nova ADR.
- [ ] Migração, reversibilidade e rollback foram avaliados.

### Segurança e privacidade

- [ ] Não há segredo, chave, token, cookie, conexão real, dado pessoal ou `credentials.json` no diff.
- [ ] Autenticação, autorização horizontal/vertical, CSRF/Origin, CORS e rate limit foram avaliados quando aplicáveis.
- [ ] Logs e erros não expõem credenciais, cookies, stack traces ou payload bruto de provider.
- [ ] Coleta, retenção e exposição de dados pessoais foram minimizadas.
- [ ] A mudança não executa deploy, login externo, contratação, cobrança, push ou publicação sem autorização.

### Dados e licenciamento

- [ ] Provider/plano/endpoint/dataset/finalidade/modalidade possui registro aplicável na matriz.
- [ ] Uso público depende de `PUBLIC_APPROVED`; estado ausente/desconhecido falha fechado.
- [ ] Fonte, timestamps, `DataLevel`, `Freshness` e limitações são preservados.
- [ ] Fallback usa apenas snapshot validado como `STALE` ou retorna `UNAVAILABLE`.
- [ ] `DEMO`, autenticação admin e feature flag não foram tratados como licença.

### Conteúdo financeiro

- [ ] Conteúdo usa somente `FACT`, `THIRD_PARTY_CONSENSUS`, `CONDITIONAL_SCENARIO`, `RISK` ou `LIMITATION`.
- [ ] Não há recomendação, sinal, promessa de retorno, preço-alvo próprio ou aconselhamento personalizado.
- [ ] Disclaimer está visível e não substitui fonte, licença ou revisão humana.
- [ ] Morning Call/publicação respeita validação, revisão humana e versões append-only.

### Interface e acessibilidade

- [ ] Fluxos alterados funcionam por teclado com foco visível.
- [ ] Contraste e semântica não dependem somente de cor.
- [ ] Visualizações têm alternativa textual/tabular equivalente.
- [ ] Movimento respeita `prefers-reduced-motion`; P1 possui feature flag e fallback.
- [ ] Estados loading, vazio, erro, `STALE` e `UNAVAILABLE` foram cobertos.

## Riscos e pendências

- Riscos técnicos/segurança/licença/custo/produto:
- Pendências explícitas:
- Plano de rollback:

## Ações externas

- [ ] Nenhuma ação externa foi executada.
- [ ] Ou: ação externa autorizada, com escopo/evidência descritos abaixo.

Autorização/evidência:
