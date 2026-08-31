"""Add idempotency storage for critical mutations."""
from alembic import op

revision = "20260831_0002"
down_revision = "20260831_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE idempotency_keys (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(), key VARCHAR(128) NOT NULL,
      method VARCHAR(16) NOT NULL, path TEXT NOT NULL, body_hash CHAR(64) NOT NULL,
      response_json JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE(key, method, path)
    )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS idempotency_keys")
