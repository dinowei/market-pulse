# ADR-027: Dados reais no staging privado, por decisão do responsável

- Status: Accepted
- Data: 2026-10-12
- Decisores: responsável humano pelo produto (pediu "sair do modo DEMO no staging" e usar
  os providers com credencial configurada); implementação por Claude Code
- Relação:
  - [ADR-025](025-provider-registry-and-lifecycle.md) (registro e camada canônica);
  - [política de integridade](../policies/FINANCIAL_DATA_AND_PORTFOLIO_INTEGRITY_POLICY.md);
  - [matriz de licenças](../DATA_PROVIDER_LICENSE_MATRIX.md);
  - [relatório de integração](../providers/PROVIDER_INTEGRATION_REPORT_DAY_41.md).

## Contexto

O staging usava valores sintéticos fora do modo DEMO:
- **Cotações:** uma cotação de demonstração para PETR4 e AAPL.
- **Benchmarks:** níveis fixos.
- **Carteira:** preço 42,42 e câmbio 5,00.

Todos vinham rotulados DEMO, mas eram o padrão de um ambiente que deveria ter dado real. O
responsável cadastrou chaves de brapi, Twelve Data, Alpha Vantage, Open Exchange Rates e
Massive no Render e no `.env` local, e pediu dados reais no staging.

A política exige `PUBLIC_APPROVED`, por decisão humana e documental, para que dado real
chegue à API pública. Nenhuma das cinco fontes tem os termos de uso revisados. O staging é
privado por escopo: uma conta, cadastro fechado. A URL, porém, é acessível a qualquer um.

## Decisão

1. **Aprovação do responsável para uso privado.** A variável
   `MARKET_PULSE_REAL_DATA_PROVIDERS` lista os providers que o responsável aprovou para o
   staging privado. O status de licença dessas respostas é `OWNER_APPROVED_PRIVATE_STAGING`,
   que não equivale a `PUBLIC_APPROVED`.
2. **Só a sessão do responsável vê dado real.**
   - Quem acessa sem sessão recebe `UNAVAILABLE` com o motivo `SESSION_REQUIRED`, nunca DEMO.
   - As respostas levam `Cache-Control: private, no-store` e `Vary: Cookie`.
3. **A API recusa subir quando a lista não é vazia e qualquer uma destas condições vale:**
   - o ambiente é `production`;
   - o DEMO está ligado (DEMO e dado real nunca se misturam);
   - o cadastro está aberto;
   - a lista inclui um provider bloqueado ou desconhecido (a B3 for Developers fica sempre
     fora).
4. **Sem DEMO por acidente.** Num ambiente protegido sem providers configurados, a resposta
   é `UNAVAILABLE` com `PROVIDER_NOT_CONFIGURED`. O DEMO continua existindo para
   desenvolvimento local, testes, fixtures e o ambiente DEMO explícito.
5. **Precedência:** a ordem do responsável, adaptada aos normalizadores que existem.

   | Dado | Ordem |
   | --- | --- |
   | Cotação no Brasil | brapi |
   | Cotação nos EUA | Twelve Data, Massive (último fechamento diário), Alpha Vantage |
   | Série diária no Brasil | brapi, só com preço sem ajuste (`includeRaw`) |
   | Série diária nos EUA | Twelve Data (`adjust=none`), Massive (`adjusted=false`) |
   | Câmbio USD/BRL | Open Exchange Rates |

   - **Fora por falta de normalizador verificado:** a Twelve Data e a Alpha Vantage para
     câmbio, a série diária da Alpha Vantage e a HG Brasil.
   - **Sem fonte:** cripto, S&P 500, Nasdaq, CDI, IPCA e IFIX ficam `UNAVAILABLE`.
6. **Resiliência:**

   | Mecanismo | Regra |
   | --- | --- |
   | Timeout | 8 s |
   | Retry | Uma nova tentativa, com backoff, só para timeout e 5xx |
   | 429 | Pausa o provider pelo `Retry-After` (5 min sem ele) e não tenta de novo |
   | 401 | Marca a chave como `INVÁLIDA` e pausa o provider por 1 h |
   | Recusa de uma consulta | Fora do plano (403) ou formato inválido: só aquela consulta fica recusada por 1 h |
   | Circuit breaker | Abre após 3 falhas e dura 5 min |
   | Cache | Em Redis, com o processo como reserva |
   | Valor `FRESH` | brapi 30 min; Twelve Data 15 min; Alpha Vantage e Open Exchange Rates 1 h; séries e Massive 6 h |
   | Valor `STALE` | Servido por até 7 dias se a atualização falhar |
   | Cota por dia | brapi 450; Twelve Data 700 (e 7 por minuto); Alpha Vantage 20; Open Exchange Rates 30 |
   | Cota por minuto | Massive 4 |

7. **Nada inventado.**
   - Variação desconhecida fica nula, nunca `0,00%`.
   - Fonte que só informa o pregão traz `session_date` sem horário.
   - Moeda divergente do catálogo e série com problema vão para quarentena e não são servidas.
   - O `DataLevel` é o do plano gratuito descrito no registro, nunca `REAL_TIME`.
8. **Contrato:** cotação, série e benchmark ganham os campos `session_date`, `timezone`,
   `observed_at`, `quality_status`, `license_status`, `is_demo` e `fallback_used`, todos
   aditivos. A cotação e a série aceitam `session_date` no lugar do horário oficial.
9. **Credenciais:**
   - **Nome da brapi:** a variável passa a ser `BRAPI_API_KEY`, o nome que o responsável
     configurou.
   - **Estados:** o painel interno e o comando `python -m app.providers.credentials_report`
     mostram `PRESENTE`, `AUSENTE`, `INVÁLIDA` ou `NÃO LIDA PELO CÓDIGO`, nunca o valor.
10. **Carteira:**
    - **Preço de hoje:** a avaliação usa o preço real de hoje.
    - **Curva de patrimônio:** usa o fechamento de cada pregão. O câmbio atual vale só para
      hoje, então posições em outra moeda ficam sem valor nos dias anteriores.

## Consequências

- **Risco residual de licença:** os termos de uso das cinco fontes não foram revisados. Os
  planos gratuitos podem proibir exibição ou redistribuição. A restrição à sessão do
  responsável limita, mas não elimina, esse risco. Antes de abrir o produto, cada fonte
  precisa de `PUBLIC_APPROVED` com evidência, ou de troca.
- **Visitante sem sessão:** não vê mais o DEMO no staging, e sim indisponibilidade com o
  motivo.
- **Planos:** o histórico do Ibovespa pela brapi respondeu 403 (fora do plano) em
  2026-10-12. Ele fica `UNAVAILABLE` com `LICENSE_BLOCKED`, enquanto a cotação do índice
  funciona.
- **Pendente:** proventos, desdobramentos e indicadores reais. Os normalizadores de
  dividendos (brapi e Massive) não existem, e a tela de proventos segue com o bloqueio de
  licença.
