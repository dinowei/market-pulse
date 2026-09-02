from datetime import date

import psycopg

from app.core.config import get_settings


def connection() -> psycopg.Connection:
    return psycopg.connect(get_settings().database_url)


def test_central_tables_enums_and_indexes_exist() -> None:
    expected = {
        "users",
        "sessions",
        "exchanges",
        "instruments",
        "instrument_aliases",
        "providers",
        "datasets",
        "provider_dataset_licenses",
        "ingestion_batches",
        "quotes",
        "price_bars",
        "fx_rates",
        "corporate_actions",
        "watchlists",
        "watchlist_items",
        "portfolios",
        "portfolio_events",
        "portfolio_positions",
        "portfolio_cash_balances",
        "portfolio_daily_valuations",
        "audit_logs",
    }
    with connection() as conn:
        rows = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall()
        assert expected <= {row[0] for row in rows}
        enums = conn.execute("SELECT typname FROM pg_type WHERE typtype='e'").fetchall()
        expected_enums = {
            "data_level",
            "freshness",
            "content_type",
            "publication_status",
            "portfolio_event_type",
        }
        assert expected_enums <= {row[0] for row in enums}
        indexes = conn.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname='public'"
        ).fetchall()
        expected_indexes = {
            "ix_quotes_instrument_time",
            "ix_price_bars_instrument_time",
            "ix_portfolio_events_portfolio_date",
        }
        assert expected_indexes <= {row[0] for row in indexes}


def test_financial_columns_use_exact_numeric_types() -> None:
    with connection() as conn:
        rows = conn.execute("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name IN
              ('quotes','price_bars','fx_rates','corporate_actions','portfolio_events',
               'portfolio_positions','portfolio_cash_balances','portfolio_daily_valuations')
              AND column_name IN (
                'price','open','high','low','close','volume','adjusted_close','rate',
                'amount','ratio','quantity','gross_amount','fees','cash_amount','fx_rate_to_base',
                'gross_amount_per_share','net_amount_per_share','withholding_tax_rate',
                'split_ratio_from','split_ratio_to','cost_basis','balance','total_value','total_cost','pnl')
        """).fetchall()
        assert rows
        assert all(row[2] == "numeric" for row in rows)


def test_portfolio_events_are_append_only_and_reversal_is_allowed() -> None:
    with connection() as conn:
        user = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
            ("schema-test@example.invalid", "hash"),
        ).fetchone()[0]
        portfolio = conn.execute(
            "INSERT INTO portfolios (user_id, name, base_currency) "
            "VALUES (%s, %s, %s) RETURNING id",
            (user, "schema-test", "BRL"),
        ).fetchone()[0]
        event = conn.execute(
            "INSERT INTO portfolio_events (portfolio_id, event_type, event_date, "
            "currency, created_by) VALUES (%s, 'CASH_DEPOSIT', %s, 'BRL', %s) "
            "RETURNING id",
            (portfolio, date.today(), user),
        ).fetchone()[0]
        conn.commit()
        try:
            conn.execute("UPDATE portfolio_events SET note='blocked' WHERE id=%s", (event,))
            raise AssertionError("UPDATE unexpectedly succeeded")
        except psycopg.DatabaseError:
            conn.rollback()
        try:
            conn.execute("DELETE FROM portfolio_events WHERE id=%s", (event,))
            raise AssertionError("DELETE unexpectedly succeeded")
        except psycopg.DatabaseError:
            conn.rollback()
        reversal = conn.execute(
            "INSERT INTO portfolio_events (portfolio_id, event_type, event_date, "
            "currency, created_by, reversed_event_id) VALUES (%s, 'REVERSAL', %s, "
            "'BRL', %s, %s) RETURNING id",
            (portfolio, date.today(), user, event),
        ).fetchone()[0]
        assert reversal != event
        conn.execute("TRUNCATE portfolio_events, portfolios, users CASCADE")
        conn.commit()


def test_corporate_actions_pipeline_columns_and_quarantine_exist() -> None:
    with connection() as conn:
        columns = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='corporate_actions'"
            ).fetchall()
        }
        expected = {
            "dataset_id",
            "external_id",
            "external_event_key",
            "status",
            "announced_date",
            "ex_date",
            "record_date",
            "payment_date",
            "gross_amount_per_share",
            "net_amount_per_share",
            "withholding_tax_rate",
            "split_ratio_from",
            "split_ratio_to",
            "ingestion_batch_id",
            "raw_payload_record_id",
            "version",
            "supersedes_event_id",
            "corrected_event_id",
            "cancellation_reason",
            "correction_reason",
            "created_at",
            "updated_at",
        }
        assert expected <= columns
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            ).fetchall()
        }
        assert "corporate_actions_quarantine" in tables
        checks = {
            row[0]
            for row in conn.execute(
                "SELECT conname FROM pg_constraint WHERE conrelid='corporate_actions'::regclass"
            ).fetchall()
        }
        assert "corporate_actions_status_check" in checks
