"""Complete the informational portfolio ledger contract for Day 20."""

from alembic import op


revision = "20260904_0007"
down_revision = "20260903_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE portfolio_events ADD COLUMN IF NOT EXISTS occurred_at TIMESTAMPTZ")
    op.execute(
        "UPDATE portfolio_events SET occurred_at = event_date::timestamp AT TIME ZONE 'UTC' "
        "WHERE occurred_at IS NULL"
    )
    op.execute(
        "ALTER TABLE portfolio_events ALTER COLUMN occurred_at SET DEFAULT now()"
    )
    op.execute("ALTER TABLE portfolio_events ALTER COLUMN occurred_at SET NOT NULL")
    op.execute("ALTER TABLE portfolio_events ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128)")
    op.execute(
        "UPDATE portfolio_events SET idempotency_key = 'legacy:' || id::text "
        "WHERE idempotency_key IS NULL"
    )
    op.execute(
        "ALTER TABLE portfolio_events ALTER COLUMN idempotency_key SET DEFAULT "
        "('legacy:' || gen_random_uuid()::text)"
    )
    op.execute("ALTER TABLE portfolio_events ALTER COLUMN idempotency_key SET NOT NULL")
    op.execute("ALTER TABLE portfolio_events ADD COLUMN IF NOT EXISTS payload_hash CHAR(64)")
    op.execute(
        "UPDATE portfolio_events SET payload_hash = repeat('0', 64) "
        "WHERE payload_hash IS NULL"
    )
    op.execute(
        "ALTER TABLE portfolio_events ALTER COLUMN payload_hash SET DEFAULT repeat('0', 64)"
    )
    op.execute("ALTER TABLE portfolio_events ALTER COLUMN payload_hash SET NOT NULL")
    op.execute(
        "ALTER TABLE portfolio_events ADD COLUMN IF NOT EXISTS request_id VARCHAR(128) "
        "NOT NULL DEFAULT 'legacy'"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_portfolio_events_idempotency "
        "ON portfolio_events (portfolio_id, idempotency_key)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_portfolio_events_reversal_target "
        "ON portfolio_events (reversed_event_id) WHERE reversed_event_id IS NOT NULL"
    )
    op.execute(
        "ALTER TABLE portfolio_events ADD CONSTRAINT portfolio_events_positive_values_check "
        "CHECK ((quantity IS NULL OR quantity > 0) AND (price IS NULL OR price > 0) "
        "AND (gross_amount IS NULL OR gross_amount > 0) AND (fees IS NULL OR fees >= 0) "
        "AND (cash_amount IS NULL OR cash_amount > 0))"
    )
    op.execute(
        """CREATE OR REPLACE FUNCTION prevent_portfolio_base_currency_change()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.base_currency <> OLD.base_currency THEN
                RAISE EXCEPTION 'portfolio base currency is immutable';
            END IF;
            RETURN NEW;
        END;
        $$;"""
    )
    op.execute(
        """CREATE TRIGGER portfolios_base_currency_immutable
        BEFORE UPDATE ON portfolios FOR EACH ROW
        EXECUTE FUNCTION prevent_portfolio_base_currency_change();"""
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS portfolios_base_currency_immutable ON portfolios")
    op.execute("DROP FUNCTION IF EXISTS prevent_portfolio_base_currency_change()")
    op.execute(
        "ALTER TABLE portfolio_events DROP CONSTRAINT IF EXISTS "
        "portfolio_events_positive_values_check"
    )
    op.execute("DROP INDEX IF EXISTS uq_portfolio_events_reversal_target")
    op.execute("DROP INDEX IF EXISTS uq_portfolio_events_idempotency")
    op.execute("ALTER TABLE portfolio_events DROP COLUMN IF EXISTS request_id")
    op.execute("ALTER TABLE portfolio_events DROP COLUMN IF EXISTS payload_hash")
    op.execute("ALTER TABLE portfolio_events DROP COLUMN IF EXISTS idempotency_key")
    op.execute("ALTER TABLE portfolio_events DROP COLUMN IF EXISTS occurred_at")
