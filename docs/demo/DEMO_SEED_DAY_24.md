# Dia 24 — Demonstração local isolada

Status: **implementado e validado localmente em 2026-09-07**.

## Propósito e limites

O Dia 24 prepara uma demonstração local, determinística e persistida para o
Market Pulse. Ela usa somente o banco dedicado **market_pulse_demo**, PostgreSQL
e Redis locais, migrations e serviços de domínio já existentes. Não existe
provider externo, dado financeiro real, scraping, licença pública, Stripe,
corretora, IA ativa, push ou deploy neste fluxo.

Todo dado de mercado demonstrado é sintético, fictício e identificado como
**DataLevel=DEMO**. Dados históricos usam o corte fixo
2026-01-30T20:00:00Z e permanecem **STALE**; não podem ser promovidos a preço
atual ou em tempo real. A fonte e a proveniência permanecem visíveis nas rotas e
na interface. A demonstração é factual e informativa, nunca recomendação de
investimento.

## Alvo único e fail closed

Os comandos administrativos recusam o alvo quando alguma verificação falha ou é
ambígua. As barreiras cumulativas são:

- APP_ENV local/development/test coerente com MARKET_PULSE_ENVIRONMENT local/test;
- MARKET_PULSE_DEMO_ENABLED exatamente true;
- URL DEMO dedicada, sem fallback para a conexão principal;
- nome do banco exatamente market_pulse_demo;
- host de loopback local, porta válida, usuário explícito e esquema PostgreSQL;
- ausência de query, fragmento e overrides libpq ambíguos;
- confirmação interna fixa no código;
- MARKET_PULSE_DATABASE_URL igual à URL DEMO durante a operação;
- para bootstrap ou reset, MARKET_PULSE_DEMO_ALLOW_RECREATE exatamente true;
- marcador de propriedade DEMO, revision Alembic e conexão administrativa
  verificados antes de qualquer drop/create.

O seed recusa qualquer linha pré-existente fora de alembic_version. O reset
rejeita dados desconhecidos, banco errado, ambiente de produção,
sessões externas ou cache sem marcador de propriedade. Ele não usa TRUNCATE,
DELETE de ledger, FLUSHDB, desabilitação de trigger ou bypass de imutabilidade.
O banco principal **market_pulse** não é alvo de reset, seed, migration de teste
ou limpeza.

## Operação local

Configure as variáveis no ambiente do processo a partir de .env.example, sem
versionar credenciais. A configuração DEMO é desativada por padrão. No mesmo
processo administrativo, MARKET_PULSE_DATABASE_URL deve ser exatamente igual a
MARKET_PULSE_DEMO_DATABASE_URL e MARKET_PULSE_REDIS_URL deve apontar ao Redis
local no DB 15. Qualquer divergência é recusada.

Com Docker Desktop usando Linux containers:

~~~powershell
docker compose up -d --wait --wait-timeout 60
python -m uv run --no-sync --offline --directory apps/api python -m app.demo check-target
~~~

O segundo comando deve retornar CONFIGURATION_ONLY para market_pulse_demo. Ele
valida configuração, não conecta nem escreve.

Para inicializar do zero, habilite a flag de lifecycle somente na sessão local e
execute bootstrap_demo. Ele cria **somente** um market_pulse_demo inexistente,
atribui o marcador DEMO e aplica migrations; se esse banco já existir, o comando
recusa a operação e nunca faz drop.

~~~powershell
python -m uv run --no-sync --offline --directory apps/api python -m app.demo bootstrap_demo
python -m uv run --no-sync --offline --directory apps/api python -m app.demo seed_demo
~~~

Para validar migrations em um banco DEMO vazio já autorizado, use upgrade,
downgrade e upgrade antes do seed. Para recriar explicitamente o DEMO, pare API
e workers locais que possam manter conexões, mantenha a flag de lifecycle
habilitada e execute reset_demo:

~~~powershell
python -m uv run --no-sync --offline --directory apps/api alembic upgrade head
python -m uv run --no-sync --offline --directory apps/api alembic downgrade base
python -m uv run --no-sync --offline --directory apps/api alembic upgrade head
python -m uv run --no-sync --offline --directory apps/api python -m app.demo reset_demo
python -m uv run --no-sync --offline --directory apps/api python -m app.demo seed_demo
~~~

Nunca substitua essas barreiras por comandos manuais de drop, limpeza de tabelas
ou alteração de triggers.

As contas usadas pelo cenário possuem uma credencial **fictícia e exclusiva do
DEMO local**, definida internamente pelo seed e não em .env. Ela não é token,
segredo de produção ou credencial reutilizável fora da demonstração.

## Dados sintéticos persistidos

O seed é determinístico e passa pelos serviços existentes de autenticação,
watchlists, carteira/ledger, market data e editorial:

- 11 instrumentos sintéticos, com canonical_id próprio;
- 3.113 barras diárias e 385 barras intradiárias;
- quatro eventos corporativos sintéticos;
- dois usuários locais DEMO, duas watchlists, quatro favoritos e duas carteiras;
- 12 eventos append-only de carteira;
- três Morning Calls publicados, com blocos, fontes e aviso informativo.

As carteiras exercitam custo, posição, caixa, P&L, rentabilidade e equity curve.
O gráfico patrimonial usa valores monetários e datas reais, aceita patrimônio
inicial zero e não conecta pontos ausentes. Gráficos de preço também preservam
lacunas; PRICE e INDEX_100 mantêm respectivamente os valores reais e a
comparação normalizada.

Corporate actions são demonstrativos e não aplicam ajustes destrutivos ao ledger.
Para tabelas legadas sem coluna DataLevel, a proveniência DEMO equivalente é
mantida por provider e dataset sintéticos.

## Reprodutibilidade e validação

Um seed completo retorna o fingerprint lógico:

~~~text
7cfa98eea76aa9f645d8e92701d2aa88834bf8d7b00b4e2a9b52df37cbcc55b5
~~~

Executar seed_demo novamente não duplica dados e retorna DEMO_ALREADY_SEEDED.
Executar reset_demo seguido de seed_demo repete o mesmo fingerprint e as mesmas
contagens lógicas; IDs técnicos, salts de autenticação e timestamps de auditoria
não são usados como evidência de igualdade semântica.

### Ordem dos gates que escrevem no DEMO

A suíte backend comum deve rodar antes dos testes de persistência opt-in. Alguns
testes de schema exercitam a imutabilidade usando operações de limpeza somente
no alvo de teste configurado; portanto, depois dessa suíte a sequência
obrigatória é reset_demo seguido de seed_demo, e somente então os testes opt-in
de persistência/reset. Essa ordem restaura um cenário DEMO com marcador de
auditoria íntegro sem limpar tabelas, desabilitar triggers ou fazer qualquer
operação no banco principal market_pulse. Se o seed encontrar dados sem o
marcador esperado, ele deve continuar recusando a operação.

Os gates executados no Dia 24 foram:

- Docker Compose saudável com PostgreSQL e Redis;
- migrations upgrade, downgrade e upgrade em schema DEMO vazio;
- reset/seed duas vezes, no-op idempotente e testes opt-in de persistência/reset;
- suíte backend, Ruff check, scans de segredos, yfinance e tipos financeiros;
- lint, typecheck, testes e build do frontend;
- health live e ready com PostgreSQL e Redis;
- Playwright local: fluxo principal e isolamento A/B.

Lint, typecheck, testes e build do frontend passam. Ruff check passa; Ruff
format --check ainda aponta formatação legada em 14 arquivos fora do escopo do
Dia 24. Revisão manual de licenças e vulnerabilidades continua necessária antes
de uma release.

## Encerramento

Após validação, encerre somente os recursos do projeto:

~~~powershell
docker compose down
~~~

Não derrube serviços não pertencentes ao projeto nem o Docker Desktop inteiro.
