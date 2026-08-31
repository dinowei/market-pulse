"""Create central schema and append-only portfolio ledger."""
from alembic import op

revision = "20260831_0001"
down_revision = None
branch_labels = None
depends_on = None

TABLES = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TYPE data_level AS ENUM ('REAL_TIME','DELAYED','EOD','DEMO');
CREATE TYPE freshness AS ENUM ('FRESH','STALE','UNAVAILABLE');
CREATE TYPE content_type AS ENUM ('FACT','CONSENSUS','CONDITIONAL_SCENARIO','RISK','LIMITATION');
CREATE TYPE publication_status AS ENUM ('DRAFT','VALIDATION_FAILED','VALIDATED','IN_REVIEW','PUBLISHED','SUPERSEDED');
CREATE TYPE portfolio_event_type AS ENUM ('BUY','SELL','CASH_DEPOSIT','CASH_WITHDRAWAL','FEE','DIVIDEND','SPLIT','ADJUSTMENT','REVERSAL');
CREATE TABLE users (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email VARCHAR(320) NOT NULL UNIQUE, password_hash TEXT NOT NULL, status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE sessions (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id), session_hash TEXT NOT NULL UNIQUE, expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX ix_sessions_user_id ON sessions(user_id);
CREATE TABLE exchanges (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), code VARCHAR(16) NOT NULL UNIQUE, name TEXT NOT NULL, country CHAR(2) NOT NULL CHECK (length(country)=2), timezone TEXT NOT NULL, currency CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'), created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE instruments (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), exchange_id UUID NOT NULL REFERENCES exchanges(id), symbol VARCHAR(32) NOT NULL, name TEXT NOT NULL, instrument_type VARCHAR(32) NOT NULL, currency CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'), status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(exchange_id, symbol));
CREATE TABLE instrument_aliases (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), instrument_id UUID NOT NULL REFERENCES instruments(id), alias_symbol VARCHAR(64) NOT NULL, source TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(instrument_id, alias_symbol, source));
CREATE TABLE providers (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name TEXT NOT NULL UNIQUE, status VARCHAR(32) NOT NULL DEFAULT 'UNAPPROVED', created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE datasets (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), provider_id UUID NOT NULL REFERENCES providers(id), name TEXT NOT NULL, status VARCHAR(32) NOT NULL DEFAULT 'UNAPPROVED', purpose TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(provider_id, name));
CREATE TABLE provider_dataset_licenses (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), provider_id UUID NOT NULL REFERENCES providers(id), dataset_id UUID NOT NULL REFERENCES datasets(id), review_status VARCHAR(32) NOT NULL DEFAULT 'DENIED', evidence_uri TEXT, reviewed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(provider_id, dataset_id));
CREATE TABLE ingestion_batches (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), provider_id UUID NOT NULL REFERENCES providers(id), dataset_id UUID NOT NULL REFERENCES datasets(id), status VARCHAR(32) NOT NULL, started_at TIMESTAMPTZ NOT NULL, finished_at TIMESTAMPTZ, error_code TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE quotes (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), instrument_id UUID NOT NULL REFERENCES instruments(id), provider_id UUID NOT NULL REFERENCES providers(id), price NUMERIC(24,8) NOT NULL, currency CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'), data_level data_level NOT NULL, freshness freshness NOT NULL, source_timestamp TIMESTAMPTZ NOT NULL, collected_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(instrument_id, provider_id, source_timestamp));
CREATE INDEX ix_quotes_instrument_time ON quotes(instrument_id, source_timestamp DESC);
CREATE TABLE price_bars (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), instrument_id UUID NOT NULL REFERENCES instruments(id), provider_id UUID NOT NULL REFERENCES providers(id), interval VARCHAR(16) NOT NULL, open NUMERIC(24,8) NOT NULL, high NUMERIC(24,8) NOT NULL, low NUMERIC(24,8) NOT NULL, close NUMERIC(24,8) NOT NULL, volume NUMERIC(32,8), adjusted_close NUMERIC(24,8), currency CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'), source_timestamp TIMESTAMPTZ NOT NULL, collected_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(instrument_id, provider_id, interval, source_timestamp));
CREATE INDEX ix_price_bars_instrument_time ON price_bars(instrument_id, source_timestamp DESC);
CREATE TABLE fx_rates (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), provider_id UUID NOT NULL REFERENCES providers(id), base_currency CHAR(3) NOT NULL CHECK (base_currency ~ '^[A-Z]{3}$'), quote_currency CHAR(3) NOT NULL CHECK (quote_currency ~ '^[A-Z]{3}$'), rate NUMERIC(24,10) NOT NULL, source_timestamp TIMESTAMPTZ NOT NULL, collected_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(provider_id, base_currency, quote_currency, source_timestamp));
CREATE TABLE corporate_actions (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), instrument_id UUID NOT NULL REFERENCES instruments(id), provider_id UUID NOT NULL REFERENCES providers(id), action_type VARCHAR(32) NOT NULL, effective_date DATE NOT NULL, declared_date DATE, amount NUMERIC(24,8), currency CHAR(3) CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$'), ratio NUMERIC(24,10), source_timestamp TIMESTAMPTZ NOT NULL, collected_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE watchlists (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id), name TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(user_id, name));
CREATE TABLE watchlist_items (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE, instrument_id UUID NOT NULL REFERENCES instruments(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(watchlist_id, instrument_id));
CREATE TABLE portfolios (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id), name TEXT NOT NULL, base_currency CHAR(3) NOT NULL CHECK (base_currency ~ '^[A-Z]{3}$'), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), archived_at TIMESTAMPTZ, UNIQUE(user_id, name));
CREATE TABLE portfolio_events (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), portfolio_id UUID NOT NULL REFERENCES portfolios(id), instrument_id UUID REFERENCES instruments(id), event_type portfolio_event_type NOT NULL, event_date DATE NOT NULL, quantity NUMERIC(24,8), price NUMERIC(24,8), gross_amount NUMERIC(24,8), fees NUMERIC(24,8), cash_amount NUMERIC(24,8), currency CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'), fx_rate_to_base NUMERIC(24,10), reversed_event_id UUID REFERENCES portfolio_events(id), source TEXT NOT NULL DEFAULT 'USER', note TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_by UUID NOT NULL REFERENCES users(id), CHECK (event_type IN ('CASH_DEPOSIT','CASH_WITHDRAWAL') OR instrument_id IS NOT NULL OR event_type='REVERSAL'), CHECK (reversed_event_id IS NULL OR event_type='REVERSAL'));
CREATE INDEX ix_portfolio_events_portfolio_date ON portfolio_events(portfolio_id, event_date, created_at);
CREATE TABLE portfolio_positions (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), portfolio_id UUID NOT NULL REFERENCES portfolios(id), instrument_id UUID NOT NULL REFERENCES instruments(id), as_of_date DATE NOT NULL, quantity NUMERIC(24,8) NOT NULL, cost_basis NUMERIC(24,8) NOT NULL, base_currency CHAR(3) NOT NULL CHECK (base_currency ~ '^[A-Z]{3}$'), calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(portfolio_id, instrument_id, as_of_date));
CREATE TABLE portfolio_cash_balances (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), portfolio_id UUID NOT NULL REFERENCES portfolios(id), as_of_date DATE NOT NULL, currency CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'), balance NUMERIC(24,8) NOT NULL, calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(portfolio_id, as_of_date, currency));
CREATE TABLE portfolio_daily_valuations (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), portfolio_id UUID NOT NULL REFERENCES portfolios(id), as_of_date DATE NOT NULL, total_value NUMERIC(24,8) NOT NULL, total_cost NUMERIC(24,8) NOT NULL, pnl NUMERIC(24,8) NOT NULL, base_currency CHAR(3) NOT NULL CHECK (base_currency ~ '^[A-Z]{3}$'), calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(portfolio_id, as_of_date));
CREATE TABLE audit_logs (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), entity_type TEXT NOT NULL, entity_id UUID, action TEXT NOT NULL, actor_user_id UUID REFERENCES users(id), occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(), metadata JSONB NOT NULL DEFAULT '{}'::jsonb);
CREATE OR REPLACE FUNCTION prevent_immutable_portfolio_event_change() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'portfolio_events are append-only'; END; $$;
CREATE TRIGGER portfolio_events_immutable_update BEFORE UPDATE ON portfolio_events FOR EACH ROW EXECUTE FUNCTION prevent_immutable_portfolio_event_change();
CREATE TRIGGER portfolio_events_immutable_delete BEFORE DELETE ON portfolio_events FOR EACH ROW EXECUTE FUNCTION prevent_immutable_portfolio_event_change();
"""


def upgrade() -> None:
    op.execute(TABLES)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_logs, portfolio_daily_valuations, portfolio_cash_balances, portfolio_positions, portfolio_events, portfolios, watchlist_items, watchlists, corporate_actions, fx_rates, price_bars, quotes, ingestion_batches, provider_dataset_licenses, datasets, providers, instrument_aliases, instruments, exchanges, sessions, users CASCADE; DROP TYPE IF EXISTS portfolio_event_type, publication_status, content_type, freshness, data_level CASCADE;")
