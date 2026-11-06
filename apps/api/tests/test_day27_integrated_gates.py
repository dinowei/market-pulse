"""Opt-in PostgreSQL integration gates for Day 27 marker and telemetry boundaries."""

from __future__ import annotations

import json
import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app.contracts import MarkerSourceType
from app.demo.operations import demo_settings, seed_demo
from app.main import app
from app.portfolios.day27 import PostgresPortfolioDay27Service

pytestmark = pytest.mark.skipif(
    os.environ.get("MARKET_PULSE_DEMO_INTEGRATION") != "true",
    reason="requires an explicitly authorized market_pulse_demo integration database",
)


def _seeded_demo_settings():
    settings = demo_settings()
    outcome = seed_demo()
    assert outcome["status"] in {"DEMO_SEEDED", "DEMO_ALREADY_SEEDED"}
    return settings


def test_all_demo_portfolio_markers_reference_persisted_rows() -> None:
    """Every returned marker is anchored to its actual ledger or corporate-action row."""
    settings = _seeded_demo_settings()
    with psycopg.connect(settings.database_url, connect_timeout=3) as connection:
        owner = connection.execute(
            "SELECT u.id,p.id FROM users u JOIN portfolios p ON p.user_id=u.id "
            "WHERE u.email='demo.a@market-pulse.local' AND p.name='Alpha Demo'"
        ).fetchone()
        assert owner is not None
        user_id, portfolio_id = (str(owner[0]), str(owner[1]))
        ledger_event_types = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT event_type FROM portfolio_events WHERE portfolio_id=%s",
                (portfolio_id,),
            ).fetchall()
        }
        action_types = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT ca.action_type FROM corporate_actions ca "
                "WHERE ca.instrument_id IN (SELECT DISTINCT instrument_id FROM portfolio_events "
                "WHERE portfolio_id=%s AND instrument_id IS NOT NULL)",
                (portfolio_id,),
            ).fetchall()
        }

    assert {"CASH_DEPOSIT", "BUY", "SELL"}.issubset(ledger_event_types)
    assert "CASH_DIVIDEND" in action_types

    markers = PostgresPortfolioDay27Service(settings).markers(user_id, portfolio_id).items
    assert markers
    assert {item.source_type for item in markers} == {
        MarkerSourceType.LEDGER_EVENT,
        MarkerSourceType.CORPORATE_ACTION,
    }

    with psycopg.connect(settings.database_url, connect_timeout=3) as connection:
        for marker in markers:
            if marker.source_type is MarkerSourceType.LEDGER_EVENT:
                source = connection.execute(
                    "SELECT 1 FROM portfolio_events WHERE id=%s AND portfolio_id=%s",
                    (marker.source_id, portfolio_id),
                ).fetchone()
            else:
                source = connection.execute(
                    "SELECT 1 FROM corporate_actions WHERE id=%s",
                    (marker.source_id,),
                ).fetchone()
            assert source is not None, f"unanchored marker: {marker.source_type}:{marker.source_id}"


def test_telemetry_endpoint_persists_only_aggregated_non_pii_columns() -> None:
    """The real endpoint stores only its aggregate contract in PostgreSQL."""
    settings = _seeded_demo_settings()
    route = f"/telemetry-integration-{uuid4().hex}"
    observed_at = "2026-01-30T20:00:00Z"
    samples = (
        ("LCP", "1234.50", 3),
        ("INP", "180", 2),
        ("CLS", "0.08", 4),
    )

    with TestClient(app) as client:
        for metric, value, sample_count in samples:
            response = client.post(
                "/api/v1/telemetry/web-vitals",
                json={
                    "metric": metric,
                    "value": value,
                    "route": route,
                    "sample_count": sample_count,
                    "observed_at": observed_at,
                },
            )
            assert response.status_code == 202
            assert response.json() == {
                "status": "accepted",
                "metric": metric,
                "route": route,
                "sample_count": sample_count,
            }

    expected_columns = {
        "id",  # technical UUID primary key; no user or session identity is stored.
        "route",
        "metric",
        "bucket_start",
        "value_sum",
        "sample_count",
        "updated_at",
    }
    prohibited_fragments = ("@", "email", "ip", "user", "name", "cookie", "token", "password")
    with psycopg.connect(
        settings.database_url, row_factory=dict_row, connect_timeout=3
    ) as connection:
        columns = {
            row["column_name"]
            for row in connection.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='web_vital_metrics'"
            ).fetchall()
        }
        assert columns == expected_columns
        persisted = connection.execute(
            "SELECT * FROM web_vital_metrics WHERE route=%s ORDER BY metric",
            (route,),
        ).fetchall()

    assert len(persisted) == len(samples)
    expected = {
        metric: (Decimal(value) * sample_count, sample_count)
        for metric, value, sample_count in samples
    }
    for row in persisted:
        assert set(row) == expected_columns
        assert row["route"] == route
        assert row["bucket_start"] == date(2026, 1, 30)
        assert row["value_sum"] == expected[row["metric"]][0]
        assert row["sample_count"] == expected[row["metric"]][1]
        serialized = json.dumps(row, default=str, sort_keys=True).casefold()
        assert not any(fragment in serialized for fragment in prohibited_fragments)
