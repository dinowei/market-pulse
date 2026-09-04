"""Add editorial roles, structured blocks and review audit events for Day 23."""

from alembic import op


revision = "20260905_0009"
down_revision = "20260905_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32) NOT NULL DEFAULT 'USER'")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT users_editorial_role_check "
        "CHECK (role IN ('USER','EDITOR','REVIEWER','ADMIN'))"
    )
    op.execute("ALTER TABLE editorial_posts ADD COLUMN IF NOT EXISTS content_date DATE")
    op.execute("ALTER TABLE editorial_posts ADD COLUMN IF NOT EXISTS current_version_id UUID")
    op.execute("ALTER TABLE editorial_posts ADD COLUMN IF NOT EXISTS published_version_id UUID")
    op.execute("ALTER TABLE editorial_posts ADD COLUMN IF NOT EXISTS created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE editorial_sources ADD COLUMN IF NOT EXISTS block_id UUID")
    op.execute(
        """DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='editorial_posts_current_version_fk') THEN
                ALTER TABLE editorial_posts ADD CONSTRAINT editorial_posts_current_version_fk
                FOREIGN KEY (current_version_id) REFERENCES editorial_post_versions(id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='editorial_posts_published_version_fk') THEN
                ALTER TABLE editorial_posts ADD CONSTRAINT editorial_posts_published_version_fk
                FOREIGN KEY (published_version_id) REFERENCES editorial_post_versions(id);
            END IF;
        END $$"""
    )
    op.execute(
        """CREATE TABLE IF NOT EXISTS editorial_blocks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            post_version_id UUID NOT NULL REFERENCES editorial_post_versions(id) ON DELETE RESTRICT,
            position INTEGER NOT NULL CHECK (position >= 0),
            content_type VARCHAR(64) NOT NULL CHECK (content_type IN ('FACT','THIRD_PARTY_CONSENSUS','CONDITIONAL_SCENARIO','RISK','LIMITATION')),
            body TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT editorial_blocks_unique_position UNIQUE (post_version_id, position)
        )"""
    )
    op.execute(
        """CREATE TABLE IF NOT EXISTS editorial_review_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            post_id UUID NOT NULL REFERENCES editorial_posts(id) ON DELETE RESTRICT,
            post_version_id UUID REFERENCES editorial_post_versions(id) ON DELETE RESTRICT,
            actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            event_type VARCHAR(64) NOT NULL,
            from_status VARCHAR(32),
            to_status VARCHAR(32),
            reason TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            request_id VARCHAR(128)
        )"""
    )
    op.execute(
        """DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='editorial_sources_block_fk') THEN
                ALTER TABLE editorial_sources ADD CONSTRAINT editorial_sources_block_fk
                FOREIGN KEY (block_id) REFERENCES editorial_blocks(id) ON DELETE RESTRICT;
            END IF;
        END $$"""
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_editorial_blocks_version_position ON editorial_blocks (post_version_id, position)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_editorial_review_events_post_created ON editorial_review_events (post_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_editorial_role ON users (role)")


def downgrade() -> None:
    op.execute("ALTER TABLE editorial_sources DROP CONSTRAINT IF EXISTS editorial_sources_block_fk")
    op.execute("ALTER TABLE editorial_posts DROP CONSTRAINT IF EXISTS editorial_posts_published_version_fk")
    op.execute("ALTER TABLE editorial_posts DROP CONSTRAINT IF EXISTS editorial_posts_current_version_fk")
    op.execute("DROP INDEX IF EXISTS ix_users_editorial_role")
    op.execute("DROP INDEX IF EXISTS ix_editorial_review_events_post_created")
    op.execute("DROP INDEX IF EXISTS ix_editorial_blocks_version_position")
    op.execute("DROP TABLE IF EXISTS editorial_review_events")
    op.execute("DROP TABLE IF EXISTS editorial_blocks")
    op.execute("ALTER TABLE editorial_sources DROP COLUMN IF EXISTS block_id")
    op.execute("ALTER TABLE editorial_posts DROP COLUMN IF EXISTS created_by_user_id")
    op.execute("ALTER TABLE editorial_posts DROP COLUMN IF EXISTS published_version_id")
    op.execute("ALTER TABLE editorial_posts DROP COLUMN IF EXISTS current_version_id")
    op.execute("ALTER TABLE editorial_posts DROP COLUMN IF EXISTS content_date")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_editorial_role_check")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS role")
