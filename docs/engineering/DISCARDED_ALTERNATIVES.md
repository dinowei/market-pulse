# Alternativas descartadas (registro do Dia 40)

- **Data:** 2026-10-07.
- **Finalidade:** registrar o que foi considerado e não adotado, com o motivo e a
  condição que reabriria a discussão. Descartar não é proibir para sempre: cada item diz
  o que precisaria mudar. Mudar qualquer decisão abaixo exige nova ADR.

| Alternativa | Motivo do descarte | Fonte | Reabrir se |
| --- | --- | --- | --- |
| **Rust** no backend | O backend é um monólito Python/FastAPI e não há gargalo de CPU medido. As páginas estáticas responderam com TTFB mediano de 45 a 59 ms, e a API aquecida respondeu ao health em 0,3 a 0,6 s; o problema medido é a hibernação do plano grátis (H-27), que a linguagem não resolve | [ADR-001](../adr/001-modular-monolith.md); [Dia 38](PERFORMANCE_DAY_38.md) | Um perfil de produção mostrar CPU como gargalo de um caminho crítico |
| **gRPC** | O contrato é REST versionado em `/api/v1` com OpenAPI e cliente gerado. O único cliente é o navegador, que exigiria gRPC-Web e um proxy a mais | `AGENTS.md` (Arquitetura); [API_VERSIONING.md](../API_VERSIONING.md) | Surgirem serviços internos com tráfego entre si, o que o monólito evita |
| **FDC3** (interoperabilidade entre aplicações financeiras de desktop) | O Market Pulse é uma aplicação web única, sem contêiner de desktop nem integração com outros terminais | [PROJECT_SPEC.md](../PROJECT_SPEC.md) (escopo) | O produto precisar trocar contexto com outras aplicações financeiras na mesma estação |
| **Microserviços, filas e streaming** | Sem evidência de escala que os justifique; aumentariam a operação | `AGENTS.md`; [ADR-001](../adr/001-modular-monolith.md) | Medição de carga mostrar limite do monólito |
| **TradingView Lightweight Charts** | O SVG P0 atende desempenho, acessibilidade e fidelidade; a biblioteca seria só apresentação e nunca fonte de verdade | [ADR-014](../adr/014-chart-engine-keep-svg.md) | Densidade de pontos acima do que o SVG sustenta, medida |
| **WebGL e Three.js no P0** | P1 sob feature flag; o gate de bundle recusa tokens de 3D no P0 | Diretriz §18 e §24; `scripts/day27_performance_gate.mjs` | P0 completo e verde, com alternativa sem perda de informação |
| **Paleta alternativa azul e laranja** para daltonismo | Conflita com a diretriz (laranja só para `STALE`) e com a ADR-006 (azul = `FLAT`). A simulação mostrou que sinais não cromáticos cobrem o problema | [Dia 36](../design/ACCESSIBILITY_DAY_36.md); [ADR-006](../adr/006-monochrome-financial-chart-semantics.md) | Revisão com usuários daltônicos apontar falha que os sinais não resolvem |
| **Imagem Docker para o deploy** | O Render e a Vercel constroem a partir do código; o shutdown gracioso foi medido sem imagem | H-01 no [handoff](../DAY29_HANDOFF.md) | Mudança de provedor que exija contêiner |
| **Área por valor de mercado e grupos por setor no heatmap** | Nenhum dataset aprovado traz esses campos; inventá-los violaria a política de integridade | [ADR-019](../adr/019-global-atlas-table-and-basic-heatmap.md) | Dataset `PUBLIC_APPROVED` com setor e valor de mercado |
| **Abrir a rede do Postgres do staging** para ler a telemetria | Aumentaria a superfície de ataque para uma leitura que o painel interno já oferece | [Dia 38](PERFORMANCE_DAY_38.md), P-4 | Nunca para leitura ad hoc; só com acesso controlado e registrado |
| **Reescrever a autenticação** (JWT, TOTP, e-mail) durante a Fase 2 | O usuário manteve a Fase 2 aprovada; a sessão opaca em cookie `HttpOnly` é o desenho da especificação | Decisão do usuário; [PROJECT_SPEC.md](../PROJECT_SPEC.md) | Requisito novo de segundo fator ou de integração entre domínios |

## Opções preteridas por decisão do usuário

Estas não foram descartadas por análise técnica, mas escolhidas pelo responsável entre
opções apresentadas. O motivo registrado é o da fonte; nenhum foi inferido depois.

| Escolha | Opção preterida | Fonte |
| --- | --- | --- |
| Tema global, persistido no navegador (chave `market-pulse.theme`) | Tema fixo por página | [ADR-016](../adr/016-global-persisted-theme.md), decisão 1 |
| Âmbar da importância média no calendário mantido, com a importância também em texto | Trocar a cor para cumprir "âmbar só para `STALE`" (diretriz §8) | [ADR-016](../adr/016-global-persisted-theme.md), decisão 2 (desvio aceito e registrado) |
| Downsampling da comparação multissérie no Dia 35 | Entregá-lo ainda nos Dias 31 a 34 | [ADR-016](../adr/016-global-persisted-theme.md), decisão 3; entregue pela [ADR-018](../adr/018-portfolio-overview-and-aligned-downsampling.md) |
| Manter a Fase 2 aprovada | Reescrever a autenticação e criar endpoint de carteira de demonstração | Decisão do usuário durante o Dia 29 (tabela acima) |

## Fora de cogitação por regra do repositório

| Opção | Regra |
| --- | --- |
| Copiar autenticação ou código de outro projeto (por exemplo, o FraudShield) | `AGENTS.md`: "Não acesse, copie ou altere o FraudShield nem outro projeto" |
| Alegar tempo real ou streaming (WebSocket) no beta | `AGENTS.md` e a política de conteúdo: dados `DEMO`, `DELAYED`, `EOD` ou `STALE` nunca são apresentados como tempo real; streaming exige provider licenciado e nova arquitetura |
