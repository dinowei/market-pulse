"""Add safe operational audit fields for the Day 25 admin system."""

from alembic import op

revision = "20260910_0010"
down_revision = "20260905_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS resource TEXT")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS result VARCHAR(32)")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS request_id VARCHAR(128)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_request_id ON audit_logs(request_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_action_occurred "
        "ON audit_logs(action, occurred_at DESC)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_status ON users(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_portfolios_active ON portfolios(archived_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ingestion_runs_started_at "
        "ON ingestion_runs(started_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_market_data_quarantine_created_at "
        "ON market_data_quarantine(created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_corporate_actions_quarantine_created_at "
        "ON corporate_actions_quarantine(created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_action_occurred")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_request_id")
    op.execute("DROP INDEX IF EXISTS ix_corporate_actions_quarantine_created_at")
    op.execute("DROP INDEX IF EXISTS ix_market_data_quarantine_created_at")
    op.execute("DROP INDEX IF EXISTS ix_ingestion_runs_started_at")
    op.execute("DROP INDEX IF EXISTS ix_portfolios_active")
    op.execute("DROP INDEX IF EXISTS ix_users_status")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS request_id")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS result")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS resource")
