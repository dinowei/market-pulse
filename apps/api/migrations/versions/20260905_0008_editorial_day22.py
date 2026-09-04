"""Add factual editorial posts, immutable versions and provenance sources."""

from alembic import op


revision = "20260905_0008"
down_revision = "20260904_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS editorial_posts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug VARCHAR(180) NOT NULL UNIQUE,
            title VARCHAR(240) NOT NULL,
            summary TEXT,
            status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
            published_at TIMESTAMPTZ,
            archived_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT editorial_posts_status_check CHECK (
                status IN ('DRAFT','UNDER_REVIEW','APPROVED','PUBLISHED','ARCHIVED')
            )
        )"""
    )
    op.execute(
        """CREATE TABLE IF NOT EXISTS editorial_post_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            post_id UUID NOT NULL REFERENCES editorial_posts(id) ON DELETE RESTRICT,
            version_number INTEGER NOT NULL CHECK (version_number > 0),
            title VARCHAR(240) NOT NULL,
            summary TEXT,
            blocks JSONB NOT NULL,
            status_snapshot VARCHAR(32) NOT NULL,
            validation_report JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            request_id VARCHAR(128),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT editorial_versions_status_check CHECK (
                status_snapshot IN ('DRAFT','UNDER_REVIEW','APPROVED','PUBLISHED','ARCHIVED')
            ),
            CONSTRAINT editorial_versions_unique_number UNIQUE (post_id, version_number)
        )"""
    )
    op.execute(
        """CREATE TABLE IF NOT EXISTS editorial_sources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            post_version_id UUID NOT NULL REFERENCES editorial_post_versions(id) ON DELETE RESTRICT,
            label VARCHAR(200) NOT NULL,
            publisher VARCHAR(200) NOT NULL,
            url VARCHAR(1000),
            source_type VARCHAR(64) NOT NULL DEFAULT 'EDITORIAL',
            retrieved_at TIMESTAMPTZ,
            justification VARCHAR(1000),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )"""
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_editorial_posts_status_published ON editorial_posts (status, published_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_editorial_versions_post_created ON editorial_post_versions (post_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_editorial_sources_version ON editorial_sources (post_version_id)")
    op.execute(
        """CREATE OR REPLACE FUNCTION prevent_published_editorial_version_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'editorial versions are append-only';
            RETURN OLD;
        END;
        $$"""
    )
    op.execute(
        """DROP TRIGGER IF EXISTS editorial_versions_append_only ON editorial_post_versions;
        CREATE TRIGGER editorial_versions_append_only
        BEFORE UPDATE OR DELETE ON editorial_post_versions
        FOR EACH ROW EXECUTE FUNCTION prevent_published_editorial_version_mutation();"""
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS editorial_versions_append_only ON editorial_post_versions")
    op.execute("DROP FUNCTION IF EXISTS prevent_published_editorial_version_mutation()")
    op.execute("DROP TABLE IF EXISTS editorial_sources")
    op.execute("DROP TABLE IF EXISTS editorial_post_versions")
    op.execute("DROP TABLE IF EXISTS editorial_posts")
