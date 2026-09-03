"""Add stable ordering and system favorites metadata to watchlists."""

from alembic import op

revision = "20260903_0006"
down_revision = "20260902_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE watchlists ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE watchlist_items ADD COLUMN IF NOT EXISTS position INTEGER")
    op.execute(
        """WITH ranked AS (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY watchlist_id ORDER BY created_at, id) - 1 AS position
            FROM watchlist_items
        )
        UPDATE watchlist_items AS items SET position = ranked.position
        FROM ranked WHERE items.id = ranked.id AND items.position IS NULL"""
    )
    op.execute("ALTER TABLE watchlist_items ALTER COLUMN position SET NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_watchlists_user_id ON watchlists(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_watchlist_items_watchlist_id ON watchlist_items(watchlist_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_watchlists_system_name ON watchlists(user_id, name) WHERE is_system")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_watchlists_system_name")
    op.execute("DROP INDEX IF EXISTS ix_watchlist_items_watchlist_id")
    op.execute("DROP INDEX IF EXISTS ix_watchlists_user_id")
    op.execute("ALTER TABLE watchlist_items DROP COLUMN IF EXISTS position")
    op.execute("ALTER TABLE watchlists DROP COLUMN IF EXISTS is_system")
