"""Add explicit adjustment, provenance and quarantine structures."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260901_0003"
down_revision: str | None = "20260831_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE price_bars ADD COLUMN adjustment_type VARCHAR(32) NOT NULL DEFAULT 'UNADJUSTED' CHECK (adjustment_type IN ('UNADJUSTED','ADJUSTED_SPLIT_ONLY','ADJUSTED_TOTAL_RETURN'))")
    op.execute("ALTER TABLE price_bars ADD COLUMN ingestion_batch_id UUID REFERENCES ingestion_batches(id)")
    op.execute("ALTER TABLE price_bars DROP CONSTRAINT IF EXISTS price_bars_instrument_id_provider_id_interval_source_timestamp_key")
    op.execute("ALTER TABLE price_bars ADD CONSTRAINT uq_price_bars_identity UNIQUE (instrument_id, provider_id, interval, source_timestamp, adjustment_type)")
    op.execute("CREATE TABLE raw_payload_records (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), provider_id UUID NOT NULL REFERENCES providers(id), dataset_id UUID NOT NULL REFERENCES datasets(id), capability VARCHAR(64) NOT NULL, request_id VARCHAR(128) NOT NULL, ingestion_batch_id UUID REFERENCES ingestion_batches(id), captured_at TIMESTAMPTZ NOT NULL, payload_hash CHAR(64) NOT NULL, payload JSONB NOT NULL, normalization_status VARCHAR(32) NOT NULL)")
    op.execute("CREATE TABLE market_data_quarantine (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), reason_code VARCHAR(64) NOT NULL, provider_id UUID REFERENCES providers(id), dataset_id UUID REFERENCES datasets(id), instrument_id UUID REFERENCES instruments(id), canonical_id TEXT, request_id VARCHAR(128), ingestion_batch_id UUID REFERENCES ingestion_batches(id), payload_hash CHAR(64), rejected_field VARCHAR(64), raw_payload_record_id UUID REFERENCES raw_payload_records(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now())")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS market_data_quarantine")
    op.execute("DROP TABLE IF EXISTS raw_payload_records")
    op.execute("ALTER TABLE price_bars DROP CONSTRAINT IF EXISTS uq_price_bars_identity")
    op.execute("ALTER TABLE price_bars ADD CONSTRAINT price_bars_instrument_id_provider_id_interval_source_timestamp_key UNIQUE (instrument_id, provider_id, interval, source_timestamp)")
    op.execute("ALTER TABLE price_bars DROP COLUMN IF EXISTS ingestion_batch_id")
    op.execute("ALTER TABLE price_bars DROP COLUMN IF EXISTS adjustment_type")
