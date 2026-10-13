# ADR-025: Registro, ciclo de vida e camada canônica de providers

- Status: Accepted (arquitetura). A precedência entre providers e qualquer ativação
  continuam pendentes de decisão humana.
- Data: 2026-10-11
- Decisores: responsável humano pelo produto (pediu a arquitetura de integração de
  providers sem ativá-los); implementação por Claude Code
- Relação: [ADR-004](004-provider-licensing-matrix.md) (matriz de licenças, `default deny`),
  H-12 no [handoff](../DAY29_HANDOFF.md), [matriz de licenças](../DATA_PROVIDER_LICENSE_MATRIX.md)
  e [matriz de onboarding](../providers/PROVIDER_ONBOARDING_MATRIX.md)

## Contexto

O backend já tinha a base para integrar fontes externas:
- interfaces por capacidade;
- gateway com licença fail-closed (`LicenseService`);
- retry com backoff e jitter;
- normalização de barras com quarentena;
- cache-aside em Redis, com lock e cache negativo;
- tabelas de ingestão e de quarentena;
- sete adapters candidatos desligados.

Faltavam cinco peças:
- um estado de ciclo de vida por provider, separado da licença de cada dataset;
- normalizadores por provider, baseados na documentação oficial;
- tratamento explícito de 429 e `Retry-After`, além de um circuit breaker;
- uma precedência com rastro de fallback;
- motivos de indisponibilidade padronizados até o frontend.

## Decisões

1. **Registro em código** (`app/providers/registry.py`), revisado por pull request. Cada
   entrada traz:
   - status, mercados, capacidades e variáveis de credencial (só os nomes);
   - autenticação, URL base, endpoints, limites e tratamento de erro documentados;
   - uso comercial, redistribuição, armazenamento e atribuição, com `None` para o que a
     fonte não declara;
   - data da verificação e as URLs oficiais usadas como evidência.
2. **Ciclo de vida:**
   - **Sequência:** `UNREVIEWED → CANDIDATE → DOCUMENTED → CONFIGURED →
     INTEGRATION_TESTED → LICENSE_REVIEW_PENDING → APPROVED → ACTIVE`, um passo por vez.
   - **Pausa:** `ACTIVE` e `PAUSED` alternam entre si.
   - **Bloqueio:** `BLOCKED` e `REVOKED` valem a partir de qualquer estado; `REVOKED` é
     terminal, e `BLOCKED` só volta para `UNREVIEWED`.
   - **Documentação não é licença:** `DOCUMENTED` só diz que a documentação oficial foi
     conferida.
3. **Ativação fail-closed** (`activation_decision`). Um provider só serve quando as três
   condições valem juntas:
   - status `ACTIVE`;
   - `license_status = PUBLIC_APPROVED`;
   - todas as credenciais presentes.

   Uma chave no ambiente sozinha não ativa nada. A licença por dataset (`LicenseService`)
   continua valendo por cima disso. O `license_status` usa o vocabulário da ADR-004
   (`UNREVIEWED`, `REJECTED`, `DEVELOPMENT_ONLY`, `PUBLIC_APPROVED`), separado do
   ciclo de vida.
4. **Camada canônica** (`app/providers/canonical.py`):
   - **Modelos:** `CanonicalQuote` e `CanonicalFxRate`; as barras reaproveitam
     `MarketBar`.
   - **Valores:** `Decimal`, sem arredondamento, com UTC e fuso obrigatório.
   - **Datas:** um timestamp no futuro é recusado. Uma fonte de fim de dia informa só a
     data do pregão, e o horário fica vazio, nunca meia-noite inventada.
   - **DEMO:** `is_demo` acompanha `data_level`.
   - **Volume ausente** continua ausente. A correção valeu também para `MarketBar`, que
     preenchia zero.
5. **Normalizadores por provider** (`app/providers/vendors.py`), só com campos confirmados
   na documentação oficial em 2026-10-11:
   - **brapi:** cotação; ticker renomeado e moeda divergente vão para quarentena.
   - **Twelve Data:** cotação e série, com `timezone=UTC`; o corpo de erro é mapeado.
   - **Alpha Vantage:** `GLOBAL_QUOTE` é EOD e usa a moeda do catálogo, com nota.
   - **Open Exchange Rates:** o 429 desse provider é falta de permissão, não limite.
   - **Massive:** barras não ajustadas, com `t` em milissegundos; paginação marcada como
     série parcial.
   - **Sem normalizador:** HG Brasil (o exemplo não traz horário da fonte) e B3 for
     Developers (sem API de cotação no catálogo público).
   - **Nível e ajuste:** `data_level` e o tipo de ajuste vêm do dataset aprovado, não do
     normalizador.
6. **Transporte** (`app/providers/http.py`):
   - consulta o registro antes de qualquer chamada;
   - injeta a credencial no envio e lê JSON com `Decimal`;
   - transforma 429 em `RATE_LIMITED`, respeitando `Retry-After`;
   - redige `apikey`, `app_id` e `key` em qualquer URL de mensagem.
7. **Resiliência:**
   - `parse_retry_after` lê segundos ou data HTTP, com teto de 1 h;
   - `backoff_delay` dá prioridade ao `Retry-After`;
   - `CircuitBreaker` fecha, abre e reabre em teste, em memória: o staging tem uma
     instância só, e uma versão em Redis só vale com várias instâncias.
8. **Precedência e fallback** (`app/providers/precedence.py`):
   - cada resposta vem de um único provider, sem costurar séries;
   - `FallbackTrace` registra o primário, quem serviu, cada tentativa e o motivo;
   - a ordem do `PRECEDENCE` é **proposta**: só vale para providers ativos e exige
     aprovação.
9. **Qualidade de série** (`app/market_data/quality.py`):
   - acusa timestamp duplicado, fora de ordem ou no futuro;
   - acusa instrumento, moeda ou ajuste misturados na mesma série;
   - `compare_sources` diz `AGREE` ou `DIVERGENT` com a tolerância informada pelo
     chamador, sem escolher nem fazer média.
10. **Motivos públicos** (`UnavailableReason`): `UNAVAILABLE`, `STALE`, `LICENSE_BLOCKED`,
    `PROVIDER_NOT_CONFIGURED`, `DATASET_NOT_APPROVED`, `SCHEMA_UNSUPPORTED`, `RATE_LIMITED`
    e `SOURCE_ERROR`. O frontend explica cada um em português e mantém o código visível
    (`src/lib/unavailable-reasons.ts`).
11. **Painel interno:** `/admin/system` mostra o registro, com as credenciais só como
    presente ou ausente e o motivo de bloqueio. O contrato ganhou
    `AdminProviderRegistryItem`, um acréscimo.

## Consequências

- **Nenhum provider ativo:** os contratos públicos de cotação não mudam, e o staging
  continua servindo DEMO e indisponível como antes.
- **Ativação exige:**
  - licença revisada;
  - chave configurada no painel do serviço;
  - teste de integração opt-in;
  - avanço de status, um passo por pull request;
  - a decisão humana sobre a precedência.
- **Ainda não feito, porque depende de provider ativo:**
  - persistir `CanonicalQuote` em `quotes`;
  - o refresh real por provider;
  - expor o rastro de fallback no contrato público.
