import psycopg

from app.core.config import get_settings


def test_canonical_id_and_market_provenance_columns_exist() -> None:
    with psycopg.connect(get_settings().database_url) as conn:
        columns = {
            (row[0], row[1]): row[2]
            for row in conn.execute(
                "SELECT table_name, column_name, data_type "
                "FROM information_schema.columns WHERE table_schema='public' "
                "AND table_name IN ('instruments','quotes','price_bars','fx_rates')"
            ).fetchall()
        }
        assert columns[("instruments", "canonical_id")] == "character varying"
        for table in ("quotes", "price_bars", "fx_rates"):
            assert (table, "dataset_id") in columns
            assert (table, "source") in columns
            assert (table, "data_level") in columns
            assert (table, "freshness") in columns
            assert (table, "ingestion_batch_id") in columns

        unique = {
            row[0]
            for row in conn.execute(
                "SELECT indexname FROM pg_indexes WHERE schemaname='public' "
                "AND tablename='instruments'"
            ).fetchall()
        }
        assert "uq_instruments_canonical_id" in unique
        assert "ix_instruments_canonical_id" in unique


def test_content_type_enum_contains_canonical_value_without_rewriting_history() -> None:
    with psycopg.connect(get_settings().database_url) as conn:
        values = {
            row[0]
            for row in conn.execute(
                "SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid "
                "WHERE t.typname='content_type'"
            ).fetchall()
        }
        assert "THIRD_PARTY_CONSENSUS" in values


def test_ingestion_runs_has_auditable_non_secret_fields() -> None:
    with psycopg.connect(get_settings().database_url) as conn:
        columns = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='ingestion_runs'"
            ).fetchall()
        }
    assert {
        "request_id",
        "job_id",
        "status",
        "started_at",
        "finished_at",
        "total_items",
        "succeeded_items",
        "failed_items",
        "quarantined_items",
        "skipped_items",
        "error_code",
        "error_message",
    } <= columns
