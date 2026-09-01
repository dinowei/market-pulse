# Framework de providers e licenciamento

O framework interno mantém o domínio independente de SDKs externos. Cada provider declara capacidades por tipo de dado e devolve `ProviderResult` com proveniência completa: provider, dataset, fonte, `source_timestamp`, `collected_at`, `data_level`, `freshness`, moeda, bolsa quando aplicável e limitações.

## Default deny

Datasets começam `UNREVIEWED`. A ausência de evidência, dataset ausente, `DEMO`, `INTERNAL_ONLY`, `EXPIRED` ou `REVOKED` bloqueiam uso público. Somente `PUBLIC_APPROVED` com evidência explícita e flag pública permite publicação. DEMO nunca concede licença.

## Adicionar provider e dataset

1. Crie um adapter em `apps/api/app/providers/` implementando somente as capacidades suportadas.
2. Não importe SDK ou tipos externos fora do adapter.
3. Registre provider e dataset com status de licença, evidência, cobertura, finalidade e modalidade de uso.
4. Submeta a aprovação documental antes de habilitar qualquer endpoint público.
5. Cubra sucesso, ausência de capacidade, timeout, rate limit, fallback e proveniência com testes.

Para aprovar, o registro precisa ser `PUBLIC_APPROVED`, possuir evidência verificável e atender à matriz de licenças. Reprovação, expiração ou revogação retornam ao bloqueio sem apagar histórico.

## Demo e indisponibilidade

`DemoProvider` é local, usa `DataLevel.DEMO`, freshness `STALE` e valores deliberadamente não representativos. Nunca é exibido como tempo real. Falhas controladas produzem `ProviderError` ou estado `UNAVAILABLE`; não expõem exceções internas, credenciais ou strings de conexão.

## Resiliência

Use `RetryPolicy` com no máximo cinco tentativas, backoff exponencial e jitter apenas para timeout/conexão. Orçamentos, rate limits e circuit breaker devem ser adicionados somente quando um provider autorizado exigir; o gateway não pode bloquear a API. Toda chamada deve ter timeout explícito no adapter.

## Testes locais

Windows PowerShell:

```powershell
$env:PYTHONPATH='.'
python -m uv run pytest tests/test_providers.py -q
python -m uv run ruff check app tests
```

Linux/macOS:

```bash
PYTHONPATH=. python -m uv run pytest tests/test_providers.py -q
python -m uv run ruff check app tests
```

Não use provider financeiro real, API externa, scraping ou segredo real nos testes. Se endpoints públicos mudarem, atualize `docs/api/openapi.json` e regenere `apps/web/src/generated/api.ts`; o Dia 6 adiciona apenas framework interno, portanto esses contratos permanecem inalterados.
