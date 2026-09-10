"""The dedicated DEMO dataset must not leak into the ordinary catalogue."""

from decimal import Decimal

import pytest

from app.core.config import Settings


def test_demo_catalog_is_selected_only_by_explicit_runtime_mode(monkeypatch):
    from app.demo import read_models
    from app.instruments import catalog

    monkeypatch.setattr(catalog, "get_settings", lambda: Settings(demo_enabled=False))
    monkeypatch.setattr(read_models, "catalog_entries", lambda: ())
    assert catalog.get_catalog() is catalog.MASTER_CATALOG
    monkeypatch.setattr(catalog, "get_settings", lambda: Settings(demo_enabled=True))
    assert catalog.get_catalog() == ()


def test_missing_demo_index_never_becomes_nominal_price():
    from datetime import datetime, timezone

    from app.demo.read_models import history_points

    points = history_points(
        [
            {
                "source_timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "open": Decimal("40"),
                "high": Decimal("41"),
                "low": Decimal("39"),
                "close": Decimal("40"),
                "volume": Decimal("100"),
            },
            {
                "source_timestamp": datetime(2026, 1, 2, tzinfo=timezone.utc),
                "open": Decimal("40"),
                "high": Decimal("45"),
                "low": Decimal("40"),
                "close": Decimal("44"),
                "volume": Decimal("110"),
            },
        ]
    )
    assert [item.value for item in points] == [Decimal("40"), Decimal("44")]
    assert [item.index_100 for item in points] == [Decimal("100"), Decimal("110")]


def test_invalid_demo_environment_fails_before_database_connection(monkeypatch):
    from app.demo.read_models import catalog_entries
    from app.demo.safety import DemoSafetyError

    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(DemoSafetyError):
        catalog_entries()


def test_demo_performance_uses_historical_marks_not_current_price_for_every_day(monkeypatch):
    from app.demo import read_models
    from app.demo.dataset import build_demo_dataset
    from app.portfolios import performance

    scenario = build_demo_dataset()
    planned = scenario.portfolios[0]
    monkeypatch.setattr(performance, "get_settings", lambda: Settings(demo_enabled=True))

    def marks(ids, as_of=None):
        result = {}
        for item in scenario.daily_bars:
            bar, p = item.bar, item.provenance
            if bar.canonical_id in ids and (as_of is None or bar.timestamp.date() == as_of):
                result[bar.canonical_id] = performance.PriceMark(
                    bar.canonical_id,
                    bar.close,
                    bar.currency,
                    p.provider,
                    p.dataset,
                    p.data_level,
                    p.freshness,
                    p.source_timestamp,
                    p.collected_at,
                    p.limitations,
                )
        return result

    monkeypatch.setattr(read_models, "price_marks", marks)
    service = performance.PortfolioPerformanceService(None)
    monkeypatch.setattr(service, "_inputs", lambda *_: (planned, list(planned.events)))
    curve = service.equity_curve_response("A", planned.id)
    assert [item.total_value_base for item in curve.points] == [
        Decimal(value) for value in ("10000", "10030", "10060", "10080", "10100")
    ]
    assert service.twr("A", planned.id).twr == Decimal("0.01")
    assert service.valuation_response("A", planned.id).as_of == scenario.cutoff
    other = scenario.portfolios[1]
    monkeypatch.setattr(service, "_inputs", lambda *_: (other, list(other.events)))
    assert service.twr("B", other.id).twr is None  # withdrawal is not at a valuation boundary


def test_missing_demo_price_has_no_fake_fx_rate_or_complete_position():
    from app.demo.dataset import build_demo_dataset
    from app.portfolios.performance import calculate_valuation

    planned = build_demo_dataset().portfolios[0]
    result = calculate_valuation(list(planned.events), base_currency="BRL", prices={}, fx_rates={})
    assert result.total_value_base is None
    assert all(item.status == "UNAVAILABLE" and item.fx_rate is None for item in result.positions)


@pytest.fixture
def demo_performance(monkeypatch):
    from app.demo import read_models
    from app.demo.dataset import build_demo_dataset
    from app.portfolios import performance

    scenario = build_demo_dataset()
    planned = scenario.portfolios[0]
    events = list(planned.events)
    monkeypatch.setattr(performance, "get_settings", lambda: Settings(demo_enabled=True))

    def marks(ids, as_of=None):
        result = {}
        for item in scenario.daily_bars:
            bar, provenance = item.bar, item.provenance
            if bar.canonical_id in ids and (as_of is None or bar.timestamp.date() == as_of):
                result[bar.canonical_id] = performance.PriceMark(
                    bar.canonical_id,
                    bar.close,
                    bar.currency,
                    provenance.provider,
                    provenance.dataset,
                    provenance.data_level,
                    provenance.freshness,
                    provenance.source_timestamp,
                    provenance.collected_at,
                    provenance.limitations,
                )
        return result

    monkeypatch.setattr(read_models, "price_marks", marks)
    service = performance.PortfolioPerformanceService(None)
    monkeypatch.setattr(service, "_inputs", lambda *_: (planned, events))
    return service, scenario, planned, events


def test_zero_beginning_equity_returns_unavailable_twr_not_an_exception(demo_performance):
    from dataclasses import replace
    from datetime import timedelta

    service, scenario, planned, events = demo_performance
    deposit = replace(planned.events[0], gross_amount=Decimal("100"))
    withdrawal = replace(
        deposit,
        id="zero-withdrawal",
        event_type="CASH_WITHDRAWAL",
        occurred_at=deposit.occurred_at + timedelta(minutes=1),
    )
    events[:] = [deposit, withdrawal]
    result = service.twr("A", planned.id)
    assert result.twr is None and result.status == "UNAVAILABLE"
    assert "POSITIVE_BEGINNING_VALUATION" in result.missing_inputs
    assert service.performance_response("A", planned.id).twr is None
    assert service.valuation_response("A", planned.id).as_of == scenario.cutoff


@pytest.mark.parametrize("after_hours", [1, 72])
def test_post_cutoff_events_do_not_change_historical_demo_valuation(demo_performance, after_hours):
    from dataclasses import replace
    from datetime import timedelta

    service, scenario, planned, events = demo_performance
    events.append(
        replace(
            planned.events[0],
            id="post-cutoff-fee",
            event_type="FEE",
            gross_amount=Decimal("100"),
            occurred_at=scenario.cutoff + timedelta(hours=after_hours),
        )
    )
    valuation = service.valuation_response("A", planned.id)
    assert valuation.as_of == scenario.cutoff
    assert valuation.total_value_base == Decimal("10100")
    assert valuation.status == "PARTIAL"
    assert "EVENTS_AFTER_DEMO_CUTOFF" in valuation.missing_inputs
    result = service.performance_response("A", planned.id)
    assert result.twr is None and result.status == "PARTIAL"
    assert "EVENTS_AFTER_DEMO_CUTOFF" in result.missing_inputs
    curve = service.equity_curve_response("A", planned.id)
    assert curve.points[-1].total_value_base == Decimal("10100")
    assert curve.points[-1].valuation_date == scenario.cutoff.date()
    assert "2026-01-30" in curve.methodology
