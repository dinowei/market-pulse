# Market Pulse

O Market Pulse é uma plataforma web autenticada para acompanhamento **informativo** de mercados financeiros. O beta de 30 dias exibirá um universo limitado de ativos, watchlist, heatmap setorial, cotações com proveniência e freshness, Morning Call inserido por comando administrativo e saúde dos providers.

> **Conteúdo informativo. Não constitui recomendação de investimento.**

## Status atual

O repositório está no **Dia 1 — Fundação, governança e inicialização**. Não há frontend, API, banco, cache, provider real, autenticação operacional, cron, billing ou deploy configurados. As tecnologias citadas são decisões arquiteturais ou alvos para os próximos dias, não serviços já instalados.

## Escopo do beta

- Dashboard responsivo em tema escuro.
- Componentes selecionados do Ibovespa para o heatmap.
- Dez ações americanas, Ibovespa, S&P 500 e Nasdaq.
- USD/BRL, ouro, Brent e WTI.
- API FastAPI versionada sob `/api/v1`.
- PostgreSQL como fonte persistente e Redis como cache/lock.
- Provider adapters substituíveis e fallback para o último snapshot válido.
- Metadados `source`, timestamps, `data_level` e estado `fresh`/`stale`.
- Cadastro por e-mail/senha com sessão opaca em cookie `HttpOnly`.
- Watchlist por usuário.
- Morning Call sem IA, inserido por comando administrativo interno e publicado com revisão humana.
- Testes essenciais, documentação e artefatos de deploy, sem publicação externa automática.

## Limites do produto

O Market Pulse é uma plataforma informativa. Seus dados e conteúdos não constituem recomendação de investimento, promessa de resultado ou orientação personalizada.

O produto não fornece comandos de compra/venda, preço-alvo próprio, timing de mercado, alocação, suitability, execução em corretora ou garantia de retorno. Dados atrasados, de fechamento ou demonstração nunca podem ser apresentados como tempo real.

Também estão fora do beta: Stripe/billing, notificações, WhatsApp, Telegram, e-mail, push, IA, aplicativos móveis, streaming tick a tick e arquitetura de alta escala.

## Arquitetura resumida

- `apps/web`: Next.js, TypeScript e Tailwind CSS, a partir do Dia 2.
- `apps/api`: FastAPI, SQLAlchemy 2 e Alembic, a partir do Dia 2.
- PostgreSQL: fonte persistente de dados válidos.
- Redis: cache não autoritativo e locks.
- Refresh: processo curto com o mesmo código da API, acionado futuramente por scheduler externo/gerenciado.
- OpenAPI: contrato entre web e API.

Leia [architecture-overview.md](architecture-overview.md) e as [ADRs](docs/adr/).

## Documentação

| Documento | Finalidade |
| --- | --- |
| [Especificação consolidada](docs/PROJECT_SPEC.md) | Escopo, decisões, hipóteses e pendências |
| [Roadmap de 30 dias](roadmap-30-days.md) | Dependências, entregáveis, riscos e critérios de aceite |
| [Arquitetura](architecture-overview.md) | Componentes, fronteiras e fluxo de dados |
| [Política financeira](financial-content-policy.md) | Limites editoriais e publicação |
| [Plano da fronteira de conteúdo](financial-content-boundary-plan.md) | Modelo append-only e validações futuras |
| [Governança de dados](docs/DATA_GOVERNANCE.md) | Proveniência, timestamps, licença e qualidade |
| [Versionamento da API](docs/API_VERSIONING.md) | Política de `/api/v1` e compatibilidade |
| [SLO inicial](docs/SLO.md) | Objetivos mensuráveis, ainda não SLA |
| [Instruções para agentes](docs/AGENTS.md) | Regras operacionais e Definition of Done |
| [Matriz de providers](docs/adr/004-provider-licensing-matrix.md) | Licença e exposição pública |

Os arquivos `docs/ARCHITECTURE.md` e `docs/ROADMAP_30_DAYS.md` permanecem como índices de compatibilidade para os nomes usados na fundação anterior.

## Configuração futura

`.env.example` contém somente nomes de variáveis e valores vazios ou claramente fictícios. Segredos reais devem ser injetados pelo shell, CI ou plataforma autorizada; nunca devem ser gravados no repositório.

As versões-alvo registradas são Node.js 24.20.0, pnpm 11.25.0 e Python 3.14.7. O host atual possui Node.js 22.19.0, npm 10.9.3 e Python 3.11.9; `pnpm` e `uv` ainda não estão instalados. A compatibilidade será validada no Dia 2 antes de qualquer lockfile.

## Verificações locais do Dia 1

```powershell
git status --short --branch --untracked-files=all
git diff --check --cached
python -m json.tool package.json
```

Build, lint, typecheck e testes de aplicação só existirão após o scaffold do Dia 2. Não descreva verificações ainda indisponíveis como aprovadas.

## Contribuição

1. Confirme no [roadmap](roadmap-30-days.md) que a tarefa pertence ao dia autorizado.
2. Leia as ADRs e políticas relacionadas.
3. Faça mudanças pequenas e revisáveis.
4. Use Conventional Commits.
5. Preencha o template de pull request e registre testes, riscos, licença e impacto de dados.
6. Não faça push, deploy ou contratação de serviços sem autorização explícita.

## Segurança

Não abra issue pública com credenciais, dados pessoais ou detalhes exploráveis. Consulte [SECURITY.md](SECURITY.md) para o processo inicial de reporte.

## Licença

Este repositório não adota licença open source neste momento. Consulte [LICENSE](LICENSE). Licenças de código e de dados financeiros são assuntos separados; nenhuma permissão de redistribuição de provider deve ser presumida.

## Próximo passo

Após revisão e aprovação desta fundação, o próximo trabalho é o **Dia 2 — Scaffold estrutural do frontend e da API**.
