# Instruções complementares para documentação

Estas regras se somam ao [`AGENTS.md` da raiz](../AGENTS.md). Em conflito, prevalece a hierarquia definida na raiz.

A baseline enterprise é o documento canônico de engenharia. Se a implementação divergir da baseline, pare antes de escrever e reporte o conflito, impacto e opção segura.

## Fontes canônicas

- Engenharia enterprise: [ENTERPRISE_ENGINEERING_BASELINE.md](engineering/ENTERPRISE_ENGINEERING_BASELINE.md)

- Produto e escopo: [PROJECT_SPEC.md](PROJECT_SPEC.md)
- Conteúdo financeiro: [FINANCIAL_CONTENT_POLICY.md](policies/FINANCIAL_CONTENT_POLICY.md)
- Integridade de dados financeiros e carteiras: [FINANCIAL_DATA_AND_PORTFOLIO_INTEGRITY_POLICY.md](policies/FINANCIAL_DATA_AND_PORTFOLIO_INTEGRITY_POLICY.md)
- Execução diária: [ROADMAP_30_DAYS.md](ROADMAP_30_DAYS.md)
- Arquitetura: [ARCHITECTURE.md](ARCHITECTURE.md)
- Plano da fronteira financeira: [financial-content-boundary.md](superpowers/plans/financial-content-boundary.md)
- Licenças operacionais: [DATA_PROVIDER_LICENSE_MATRIX.md](DATA_PROVIDER_LICENSE_MATRIX.md)
- Framework de providers: [PROVIDER_FRAMEWORK.md](PROVIDER_FRAMEWORK.md)
- Onboarding de providers: [PROVIDER_ONBOARDING_MATRIX.md](providers/PROVIDER_ONBOARDING_MATRIX.md)
- Adapters de mercado: [ADAPTERS_DAY_9.md](providers/ADAPTERS_DAY_9.md)
- Normalização de mercado: [NORMALIZATION_DAY_10.md](market_data/NORMALIZATION_DAY_10.md)
- Eventos corporativos: [CORPORATE_ACTIONS_DAY_11.md](market_data/CORPORATE_ACTIONS_DAY_11.md)
- Cache e freshness do Dia 12: [CACHE_FRESHNESS_DAY_12.md](market_data/CACHE_FRESHNESS_DAY_12.md)
- Reconciliação do roadmap do Dia 11: [DAY_11_1_ROADMAP_RECONCILIATION.md](engineering/DAY_11_1_ROADMAP_RECONCILIATION.md)
- Integridade financeira: [FINANCIAL_DATA_AND_PORTFOLIO_INTEGRITY_POLICY.md](policies/FINANCIAL_DATA_AND_PORTFOLIO_INTEGRITY_POLICY.md)
- Hardening retroativo: [DAY_10_1_RETROACTIVE_HARDENING.md](engineering/DAY_10_1_RETROACTIVE_HARDENING.md)
- Catálogo mestre: [MASTER_INSTRUMENT_CATALOG.md](instruments/MASTER_INSTRUMENT_CATALOG.md)
- Universo operacional: [P0_OPERATIONAL_UNIVERSE.md](instruments/P0_OPERATIONAL_UNIVERSE.md)
- Backlog de candidatos: [CANDIDATE_UNIVERSE_BACKLOG.md](instruments/CANDIDATE_UNIVERSE_BACKLOG.md)
- Frontend Particle Atlas: [PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md](design/PARTICLE_ATLAS_FRONTEND_DIRECTIVE.md)
- Automação operacional de mercado: [AUTOMATION_DAY_14.md](market_data/AUTOMATION_DAY_14.md)
- Gate da Semana 2: [WEEK_2_GATE.md](engineering/WEEK_2_GATE.md)
- Hardening 110% da Semana 2: [WEEK_2_110_HARDENING.md](engineering/WEEK_2_110_HARDENING.md)
- Market data público do Dia 15: [PUBLIC_MARKET_DATA_DAY_15.md](market_data/PUBLIC_MARKET_DATA_DAY_15.md)
- Reconciliação do roadmap do Dia 16: [DAY_16_ROADMAP_RECONCILIATION.md](engineering/DAY_16_ROADMAP_RECONCILIATION.md)
- Shell Particle Atlas do Dia 16: [PARTICLE_ATLAS_DAY_16_SHELL.md](design/PARTICLE_ATLAS_DAY_16_SHELL.md)
- Semântica canônica de gráficos Particle Atlas: [PARTICLE_ATLAS_CHART_SEMANTICS.md](design/PARTICLE_ATLAS_CHART_SEMANTICS.md)
- Gráficos Particle Atlas do Dia 17: [PARTICLE_ATLAS_DAY_17_CHARTS.md](design/PARTICLE_ATLAS_DAY_17_CHARTS.md)
- Reconciliação visual Particle Atlas do Dia 18.1: [PARTICLE_ATLAS_VISUAL_RECONCILIATION_DAY_18_1.md](design/PARTICLE_ATLAS_VISUAL_RECONCILIATION_DAY_18_1.md)
- Autenticação e sessões do Dia 18: [AUTH_SESSIONS_DAY_18.md](security/AUTH_SESSIONS_DAY_18.md)
- Watchlists e favoritos do Dia 19: [WATCHLISTS_DAY_19.md](product/WATCHLISTS_DAY_19.md)
- Carteiras informativas do Dia 20: [PORTFOLIOS_DAY_20.md](product/PORTFOLIOS_DAY_20.md)
- Reconciliação do roadmap do Dia 20: [DAY_20_ROADMAP_RECONCILIATION.md](engineering/DAY_20_ROADMAP_RECONCILIATION.md)
- Performance factual de carteiras do Dia 21: [PORTFOLIO_PERFORMANCE_DAY_21.md](product/PORTFOLIO_PERFORMANCE_DAY_21.md)
- Morning Call factual do Dia 22: [MORNING_CALL_DAY_22.md](editorial/MORNING_CALL_DAY_22.md)
- Morning Call público e administrativo do Dia 23: [MORNING_CALL_ADMIN_DAY_23.md](editorial/MORNING_CALL_ADMIN_DAY_23.md)
- Demo local validada do Dia 24: [DEMO_SEED_DAY_24.md](demo/DEMO_SEED_DAY_24.md)
- Gate da Semana 3: [WEEK_3_GATE.md](engineering/WEEK_3_GATE.md)
- Painel operacional interno do Dia 25: [ADMIN_SYSTEM_DAY_25.md](operations/ADMIN_SYSTEM_DAY_25.md)
- Comparação multiativo, benchmarks e calendário do Dia 26: [DAY_26_MULTIATIVE_CALENDAR.md](market_data/DAY_26_MULTIATIVE_CALENDAR.md)
- Proventos, marcadores e performance do Dia 27: [DAY_27_INCOME_MARKERS_PERFORMANCE.md](market_data/DAY_27_INCOME_MARKERS_PERFORMANCE.md)
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

- A política canônica de conteúdo é a única fonte normativa editorial; a política de integridade de dados financeiros e carteiras é obrigatória para dados, cálculos e exibição.
- Todo exemplo financeiro deve ser simbólico ou claramente fictício.
- Não escreva recomendação, sinal, promessa, preço-alvo próprio ou aconselhamento personalizado.
- `DEMO` e acesso interno não concedem licença.
- Exposição pública de provider exige `PUBLIC_APPROVED` na combinação exata e evidência oficial.

## Particle Atlas

Documente o P0 acessível antes do P1 visual. Não descreva Particle Atlas como provider, motor preditivo, recomendação ou garantia de tempo real. Globo 3D e efeitos avançados são condicionais, feature-flagged e não bloqueiam o beta.

Qualquer tarefa envolvendo gráficos, séries históricas, comparação de ativos,
heatmap, treemap, visualização de carteira, renda fixa, Particle Atlas ou outra
renderização financeira deve ler integralmente
`design/PARTICLE_ATLAS_CHART_SEMANTICS.md` antes de planejar ou editar.

## Gate documental

Antes de trabalhar em seed/reset, fixtures de demonstração ou E2E principal,
consulte `demo/DEMO_SEED_DAY_24.md`. O banco principal não é alvo de reset nem de
testes com limpeza. Uma preparação offline não equivale a seed persistido ou gate
integrado aprovado: execute as barreiras, migrations e validações registradas no
guia antes de declarar o resultado.

Uma mudança documental termina com:

- `git diff --check` sem erro;
- links relativos internos válidos;
- documentos canônicos não vazios e reconhecidos pelo CI;
- busca por referências antigas/contraditórias revisada;
- varredura de segredos e confirmação de ausência de código inesperado;
- diff e status completos relatados com comandos e exit codes.
