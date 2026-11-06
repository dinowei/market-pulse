"""Day 41: proventos and corporate events of one instrument, behind the license gate."""

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.demo.read_models as read_models
import app.instruments.catalog as catalog
import app.market_data.corporate_events as corporate_events
from app.core.config import Settings
from app.instruments.catalog import InstrumentCatalogEntry
from app.main import app

client = TestClient(app)
URL = "/api/v1/market-data/corporate-actions/"
STAMP = datetime(2026, 1, 20, 12, tzinfo=UTC)
ENTRY = InstrumentCatalogEntry(
    canonical_id="demo.equity.mpxa3",
    symbol="MPXA3",
    display_symbol="MPXA3",
    name="Aster DEMO",
    instrument_type="EQUITY",
    exchange="DEMO",
    country="BR",
    region="DEMO",
    currency="BRL",
    timezone="UTC",
    catalog_status="CANDIDATE",
    coverage_tier="P0_CATALOG",
    data_support_status="METADATA_ONLY",
)


def _row(**overrides) -> dict:
    row = {
        "action_type": "CASH_DIVIDEND",
        "status": "CONFIRMED",
        "ex_date": date(2026, 1, 26),
        "payment_date": date(2026, 1, 30),
        "effective_date": None,
        "gross_amount_per_share": Decimal("1.00000000"),
        "net_amount_per_share": None,
        "currency": "BRL",
        "split_ratio_from": None,
        "split_ratio_to": None,
        "provider": "demo",
        "dataset": "demo-day24-corporate-actions",
        "source_timestamp": STAMP,
        "collected_at": STAMP,
    }
    return {**row, **overrides}


def _demo(monkeypatch, rows_result) -> None:
    settings = Settings(demo_enabled=True)
    monkeypatch.setattr(catalog, "get_settings", lambda: settings)
    monkeypatch.setattr(corporate_events, "get_settings", lambda: settings)
    monkeypatch.setattr(read_models, "catalog_entries", lambda: (ENTRY,))
    monkeypatch.setattr(read_models, "corporate_action_rows", rows_result)


def test_unknown_instrument_is_404() -> None:
    assert client.get(URL + "equity.br.b3.unknown9").status_code == 404


def test_without_an_approved_dataset_the_answer_is_unavailable_not_empty() -> None:
    body = client.get(URL + "equity.br.b3.petr4").json()
    assert body["availability"] == "UNAVAILABLE"
    assert body["unavailable_reason"] == "DATASET_NOT_APPROVED"
    assert body["items"] == []


def test_demo_rows_keep_decimal_values_and_provenance(monkeypatch) -> None:
    split = _row(
        action_type="SPLIT",
        ex_date=date(2026, 2, 2),
        payment_date=None,
        gross_amount_per_share=None,
        split_ratio_from=Decimal("1"),
        split_ratio_to=Decimal("2"),
    )
    _demo(monkeypatch, lambda canonical_id: ([_row(), split], 0))
    body = client.get(URL + ENTRY.canonical_id).json()
    assert body["availability"] == "AVAILABLE"
    dividend, event = body["items"]
    assert Decimal(dividend["gross_amount_per_share"]) == Decimal("1")
    assert dividend["provenance"]["data_level"] == "DEMO"
    assert dividend["provenance"]["dataset"] == "demo-day24-corporate-actions"
    assert (event["action_type"], event["split_ratio_to"]) == ("SPLIT", "2")
    assert any("DEMO" in text for text in body["limitations"])


def test_a_withheld_row_makes_the_whole_answer_unavailable(monkeypatch) -> None:
    _demo(monkeypatch, lambda canonical_id: ([_row()], 1))
    body = client.get(URL + ENTRY.canonical_id).json()
    assert (body["availability"], body["unavailable_reason"]) == ("UNAVAILABLE", "LICENSE_BLOCKED")
    assert body["items"] == []


def test_a_source_failure_is_reported_as_unavailable(monkeypatch) -> None:
    def broken(canonical_id):
        raise ConnectionError("database down")

    _demo(monkeypatch, broken)
    body = client.get(URL + ENTRY.canonical_id).json()
    assert body["unavailable_reason"] == "SOURCE_UNAVAILABLE"


def test_the_gate_accepts_only_the_synthetic_corporate_actions_dataset(monkeypatch) -> None:
    monkeypatch.setattr(read_models, "demo_settings", lambda: SimpleNamespace(environment="local"))
    licensed = {
        "provider": "demo",
        "provider_status": "DEMO_SYNTHETIC",
        "dataset_status": "DEMO_SYNTHETIC",
        "dataset": "demo-day24-corporate-actions",
        "review_status": "DEMO_SYNTHETIC",
        "evidence_uri": "docs/demo/DEMO_SEED_DAY_24.md",
    }
    assert read_models._action_allowed(licensed)
    assert not read_models._action_allowed({**licensed, "dataset": "demo-day24-quotes"})
    assert not read_models._action_allowed({**licensed, "provider": "brapi"})
    assert not read_models._action_allowed({**licensed, "review_status": "UNREVIEWED"})
    monkeypatch.setattr(
        read_models, "demo_settings", lambda: SimpleNamespace(environment="staging")
    )
    assert not read_models._action_allowed(licensed), "synthetic data never leaves local/test"
