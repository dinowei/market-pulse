# Instruções complementares para documentação

Estas regras se somam ao [`AGENTS.md` da raiz](../AGENTS.md). Em conflito, prevalece a hierarquia definida na raiz.

## Fontes canônicas

- Produto e escopo: [PROJECT_SPEC.md](PROJECT_SPEC.md)
- Conteúdo financeiro: [FINANCIAL_CONTENT_POLICY.md](policies/FINANCIAL_CONTENT_POLICY.md)
- Execução diária: [ROADMAP_30_DAYS.md](ROADMAP_30_DAYS.md)
- Arquitetura: [ARCHITECTURE.md](ARCHITECTURE.md)
- Plano da fronteira financeira: [financial-content-boundary.md](superpowers/plans/financial-content-boundary.md)
- Licenças operacionais: [DATA_PROVIDER_LICENSE_MATRIX.md](DATA_PROVIDER_LICENSE_MATRIX.md)
- Decisões históricas aceitas: [ADRs](adr/)

Arquivos equivalentes na raiz marcados como históricos servem apenas à rastreabilidade e não competem com as fontes acima.

## Antes de editar documentos

1. Confirme o dia/subtarefa e leia integralmente as fontes aplicáveis.
2. Compare fatos, decisões, hipóteses e pendências; não promova hipótese a decisão.
3. Preserve histórico. Mudança material em ADR aceita exige nova ADR.
4. Verifique links relativos, nomes normativos, caminhos canônicos e consistência entre documentos.
5. Não atualize documento apenas para registrar que uma tarefa foi executada.

## Redação e evidência

- Não declare versão, preço, quota, plano, licença, direito, disponibilidade ou capacidade externa sem evidência atual.
- Diferencie alvo pretendido de serviço configurado; documentação nunca autoriza login, contratação ou deploy.
- Use enumerações exatas: `DataLevel`, `Freshness`, `ContentType` e status de licença não aceitam aliases informais em contratos normativos.
- Registre limitação de licença e cold start sem prometer disponibilidade/tempo real.
- Não copie conteúdo protegido nem inclua segredo, dado pessoal ou credencial em exemplo.

## Conteúdo financeiro

- A política canônica é a única fonte normativa editorial.
- Todo exemplo financeiro deve ser simbólico ou claramente fictício.
- Não escreva recomendação, sinal, promessa, preço-alvo próprio ou aconselhamento personalizado.
- `DEMO` e acesso interno não concedem licença.
- Exposição pública de provider exige `PUBLIC_APPROVED` na combinação exata e evidência oficial.

## Particle Atlas

Documente o P0 acessível antes do P1 visual. Não descreva Particle Atlas como provider, motor preditivo, recomendação ou garantia de tempo real. Globo 3D e efeitos avançados são condicionais, feature-flagged e não bloqueiam o beta.

## Gate documental

Uma mudança documental termina com:

- `git diff --check` sem erro;
- links relativos internos válidos;
- documentos canônicos não vazios e reconhecidos pelo CI;
- busca por referências antigas/contraditórias revisada;
- varredura de segredos e confirmação de ausência de código inesperado;
- diff e status completos relatados com comandos e exit codes.
