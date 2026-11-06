"""Allow only erasing portfolio_events.note under the append-only trigger (ADR-010, H-08).

The ledger stays append-only: every DELETE and every UPDATE is refused, except an
UPDATE that sets a non-null note to NULL and changes nothing else. Comparing the whole
row as JSONB (minus note) keeps the rule correct for columns added in later migrations.
"""

from alembic import op

revision = "20261005_0012"
down_revision = "20260911_0011"
branch_labels = None
depends_on = None

NOTE_ERASURE_FUNCTION = """
CREATE OR REPLACE FUNCTION prevent_immutable_portfolio_event_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.note IS NOT NULL
       AND NEW.note IS NULL
       AND (to_jsonb(NEW) - 'note') = (to_jsonb(OLD) - 'note') THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'portfolio_events are append-only';
END;
$$;
"""

ORIGINAL_FUNCTION = """
CREATE OR REPLACE FUNCTION prevent_immutable_portfolio_event_change() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'portfolio_events are append-only'; END; $$;
"""


def upgrade() -> None:
    op.execute(NOTE_ERASURE_FUNCTION)


def downgrade() -> None:
    # Erased notes stay NULL: the original text is gone by design and is not restored.
    op.execute(ORIGINAL_FUNCTION)
