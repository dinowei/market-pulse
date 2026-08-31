# Instruções para agentes e copilotos

## Antes de alterar

1. Leia a especificação, arquitetura, roadmap e documentos da área.
2. Confirme que a tarefa pertence ao dia autorizado.
3. Verifique status/diff e preserve trabalho existente.
4. Identifique fatos, decisões, hipóteses e pendências.

## Regras obrigatórias

- Não implemente feature fora do escopo sem autorização explícita.
- Nunca exponha segredo, credencial, cookie, dado pessoal ou conexão real.
- Não invente dado financeiro, fonte, endpoint, preço, quota ou licença.
- Preserve ADRs; divergências materiais exigem nova ADR.
- Atualize testes e documentação junto com comportamento.
- Prefira mudanças pequenas, reversíveis e revisáveis.
- Registre risco, pendência e evidência.
- Não sirva provider/dataset sem licença compatível com o público.
- A regra de licença deve ser de domínio, não lembrete manual.
- Respeite a [Política Canônica de Conteúdo Financeiro](policies/FINANCIAL_CONTENT_POLICY.md) e o disclaimer obrigatório.
- Não faça push, deploy, login externo ou contratação sem autorização.
- Pare quando uma decisão puder causar perda de dados, exposição indevida ou custo externo.

## Dados financeiros

- Exponha `source`, timestamps, `data_level` e freshness.
- Nunca chame `DELAYED`, `EOD` ou `DEMO` de tempo real.
- Use somente snapshots validados no fallback.
- Preserve o conteúdo publicado por versão append-only.
- Proíba recomendações, promessas, imperativos e preço-alvo próprio.

## Git e revisão

- Use Conventional Commits.
- Revise diff completo e execute checks aplicáveis antes de commit.
- Não reescreva histórico, apague trabalho ou faça push sem autorização.
- Preencha o template de PR e registre impacto de licença, dados, privacidade e migração.

## Definition of Done

Uma tarefa só está concluída quando:

- escopo e dependências do dia foram respeitados;
- critérios de aceite possuem evidência reproduzível;
- testes relevantes foram criados e executados;
- lint, typecheck e build aplicáveis passaram;
- documentação e ADRs estão consistentes;
- nenhum segredo ou dado pessoal foi incluído;
- licença/proveniência/freshness foram verificadas quando aplicável;
- conteúdo financeiro passou pela política e mantém disclaimer;
- riscos, pendências e rollback foram registrados;
- `git status` e diff foram revisados;
- verificações indisponíveis foram declaradas, não presumidas.
