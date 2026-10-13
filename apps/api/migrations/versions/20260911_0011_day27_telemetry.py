"""Store anonymous daily Core Web Vitals aggregates for Day 27."""

from alembic import op


revision = "20260911_0011"
down_revision = "20260910_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE web_vital_metrics (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            route VARCHAR(160) NOT NULL CHECK (route LIKE '/%'),
            metric VARCHAR(3) NOT NULL CHECK (metric IN ('LCP','INP','CLS')),
            bucket_start DATE NOT NULL,
            value_sum NUMERIC(30,8) NOT NULL CHECK (value_sum >= 0),
            sample_count BIGINT NOT NULL CHECK (sample_count > 0),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(route, metric, bucket_start)
        )"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS web_vital_metrics")

