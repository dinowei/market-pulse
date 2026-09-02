"""Add canonical instrument identity and provenance dimensions incrementally."""

from alembic import op

revision = "20260902_0005"
down_revision = "20260902_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preserve the historical enum label while introducing the canonical name.
    op.execute("ALTER TYPE content_type ADD VALUE IF NOT EXISTS 'THIRD_PARTY_CONSENSUS'")
    op.execute("ALTER TABLE instruments ADD COLUMN canonical_id VARCHAR(160)")
    op.execute(
        """UPDATE instruments AS i SET canonical_id =
        lower(regexp_replace(i.instrument_type, '[^a-zA-Z0-9]+', '-', 'g')) || '.' ||
        lower(regexp_replace(e.country, '[^a-zA-Z0-9]+', '-', 'g')) || '.' ||
        lower(regexp_replace(e.code, '[^a-zA-Z0-9]+', '-', 'g')) || '.' ||
        lower(regexp_replace(i.symbol, '[^a-zA-Z0-9]+', '-', 'g'))
        FROM exchanges AS e WHERE e.id = i.exchange_id"""
    )
    op.execute("ALTER TABLE instruments ALTER COLUMN canonical_id SET NOT NULL")
    op.execute("ALTER TABLE instruments ADD CONSTRAINT uq_instruments_canonical_id UNIQUE (canonical_id)")
    op.execute("CREATE INDEX ix_instruments_canonical_id ON instruments(canonical_id)")

    # quotes already carried data_level/freshness in the central schema.
    for column, definition in (
        ("dataset_id", "UUID REFERENCES datasets(id)"),
        ("source", "TEXT"),
        ("latency_ms", "INTEGER"),
        ("raw_payload_record_id", "UUID REFERENCES raw_payload_records(id)"),
    ):
        op.execute(f"ALTER TABLE quotes ADD COLUMN {column} {definition}")
    for column, definition in (
        ("dataset_id", "UUID REFERENCES datasets(id)"),
        ("source", "TEXT"),
        ("data_level", "data_level"),
        ("freshness", "freshness"),
        ("latency_ms", "INTEGER"),
        ("raw_payload_record_id", "UUID REFERENCES raw_payload_records(id)"),
    ):
        op.execute(f"ALTER TABLE price_bars ADD COLUMN {column} {definition}")
    op.execute("ALTER TABLE quotes ADD COLUMN ingestion_batch_id UUID REFERENCES ingestion_batches(id)")
    op.execute("ALTER TABLE fx_rates ADD COLUMN dataset_id UUID REFERENCES datasets(id)")
    op.execute("ALTER TABLE fx_rates ADD COLUMN source TEXT")
    op.execute("ALTER TABLE fx_rates ADD COLUMN data_level data_level")
    op.execute("ALTER TABLE fx_rates ADD COLUMN freshness freshness")
    op.execute("ALTER TABLE fx_rates ADD COLUMN latency_ms INTEGER")
    op.execute("ALTER TABLE fx_rates ADD COLUMN ingestion_batch_id UUID REFERENCES ingestion_batches(id)")
    op.execute(
        "ALTER TABLE fx_rates ADD COLUMN raw_payload_record_id UUID REFERENCES raw_payload_records(id)"
    )
    op.execute(
        """CREATE TABLE ingestion_runs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        provider_id UUID REFERENCES providers(id),
        dataset_id UUID REFERENCES datasets(id),
        capability VARCHAR(64) NOT NULL,
        status VARCHAR(32) NOT NULL,
        started_at TIMESTAMPTZ NOT NULL,
        finished_at TIMESTAMPTZ,
        request_id VARCHAR(128) NOT NULL,
        job_id VARCHAR(128) NOT NULL,
        lock_key TEXT NOT NULL,
        total_items INTEGER NOT NULL DEFAULT 0,
        succeeded_items INTEGER NOT NULL DEFAULT 0,
        failed_items INTEGER NOT NULL DEFAULT 0,
        quarantined_items INTEGER NOT NULL DEFAULT 0,
        skipped_items INTEGER NOT NULL DEFAULT 0,
        error_code TEXT,
        error_message TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(job_id)
        )"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ingestion_runs")
    op.execute("ALTER TABLE fx_rates DROP COLUMN IF EXISTS raw_payload_record_id")
    op.execute("ALTER TABLE fx_rates DROP COLUMN IF EXISTS ingestion_batch_id")
    op.execute("ALTER TABLE fx_rates DROP COLUMN IF EXISTS latency_ms")
    op.execute("ALTER TABLE fx_rates DROP COLUMN IF EXISTS freshness")
    op.execute("ALTER TABLE fx_rates DROP COLUMN IF EXISTS data_level")
    op.execute("ALTER TABLE fx_rates DROP COLUMN IF EXISTS source")
    op.execute("ALTER TABLE fx_rates DROP COLUMN IF EXISTS dataset_id")
    op.execute("ALTER TABLE quotes DROP COLUMN IF EXISTS ingestion_batch_id")
    for column in ("raw_payload_record_id", "latency_ms", "source", "dataset_id"):
        op.execute(f"ALTER TABLE quotes DROP COLUMN IF EXISTS {column}")
    for column in (
        "raw_payload_record_id",
        "latency_ms",
        "freshness",
        "data_level",
        "source",
        "dataset_id",
    ):
        op.execute(f"ALTER TABLE price_bars DROP COLUMN IF EXISTS {column}")
    op.execute("DROP INDEX IF EXISTS ix_instruments_canonical_id")
    op.execute("ALTER TABLE instruments DROP CONSTRAINT IF EXISTS uq_instruments_canonical_id")
    op.execute("ALTER TABLE instruments DROP COLUMN IF EXISTS canonical_id")
