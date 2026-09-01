# Adapters de mercado — Dia 9

O Dia 9 consolidou adapters candidatos atrás do framework interno. Nenhum provider está aprovado, ativado ou chamado por padrão.

## Adapters

`BrapiAdapter`, `HgBrasilAdapter`, `TwelveDataAdapter`, `AlphaVantageAdapter`, `OpenExchangeRatesAdapter`, `MassiveAdapter` e `B3DevelopersAdapter` compartilham uma base HTTP injetável. A base aceita transporte somente por injeção de dependência, normaliza status 401/403/429/5xx e timeout para `ProviderError`, e falha com `ProviderNotConfigured` quando token/transporte ausente.

As capabilities permanecem separadas no framework: quote, histórico, FX, metadados, dividendos e corporate actions. Nenhum adapter importa SDK externo ou expõe payload bruto ao domínio.

## Normalização e DEMO

Normalizadores convertem valores imediatamente para `Decimal`, exigem timestamp com timezone, moeda ISO 4217 e `canonical_id`. O `DemoProvider` cobre quote, OHLCV sintético, FX, metadata, dividendos e ações corporativas; tudo usa `DataLevel.DEMO`, `Freshness.STALE` e limitações explícitas.

## Raw payload retention

`RawPayloadRecord` guarda provider, dataset, capability, `request_id`, `ingestion_batch_id` opcional, timestamp, hash SHA-256, payload sanitizado e status de normalização. Chaves `authorization`, `api_key`, `token`, `secret` e `password` são redigidas antes da retenção. A retenção é técnica/auditável e deve seguir a política de dados do ambiente; não é contrato público.

## Fallback e licenciamento

`ProviderGateway.request_with_fallback` ignora datasets sem `PUBLIC_APPROVED` e só tenta fontes aprovadas. Se nenhuma estiver disponível, retorna erro controlado; nunca usa `UNREVIEWED` como fallback e nunca mistura DEMO com dado real sem identificação.

## Segurança de logs

Erros carregam código e `request_id`, provider/dataset/capability podem ser registrados por uma camada de observabilidade, mas tokens, Authorization, URLs sensíveis e payload integral não devem ser logados. Testes usam transporte falso e não fazem rede.

## Homologação futura

Revisar termos, plano, endpoint, dataset, finalidade e modalidade; registrar evidência na matriz; guardar credenciais fora do repositório; testar em staging; validar freshness, rate limit, cache e proveniência; só então solicitar mudança para `PUBLIC_APPROVED`. Alteração de rota pública exigirá atualização do OpenAPI e cliente gerado.
