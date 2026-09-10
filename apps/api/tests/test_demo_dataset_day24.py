from collections import Counter
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
from uuid import UUID

import pytest

from app.contracts import DataLevel, Freshness
from app.editorial.validator import EditorialStatus, validate_editorial_blocks
from app.instruments.catalog import MASTER_CATALOG, DataSupportStatus
from app.market_data.normalization import AdjustmentType
from app.portfolios.performance import PriceMark, calculate_valuation
from app.portfolios.service import replay_events


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Offline DEMO preparation cannot access a network")

    monkeypatch.setattr("socket.socket.connect", denied)
    monkeypatch.setattr("socket.create_connection", denied)
    monkeypatch.setattr("socket.getaddrinfo", denied)


def test_dataset_is_repeatable_without_network_or_catalog_mutation():
    from app.demo.dataset import build_demo_dataset

    original = tuple(entry.model_dump() for entry in MASTER_CATALOG)
    first = build_demo_dataset()
    with localcontext() as context:
        context.prec = 9
        second = build_demo_dataset()
    assert first == second
    assert first.fingerprint() == second.fingerprint()
    assert len(first.fingerprint()) == 64
    assert tuple(entry.model_dump() for entry in MASTER_CATALOG) == original
    assert first.cutoff == datetime(2026, 1, 30, 20, tzinfo=timezone.utc)
    assert Counter(item.instrument_type for item in first.instruments) == {
        "EQUITY": 5,
        "ETF": 2,
        "FII": 2,
        "INDEX": 2,
    }
    assert {item.symbol for item in first.instruments} == {
        "MPXA3",
        "MPXB3",
        "MPXC3",
        "MPXD3",
        "MPXE3",
        "MPET11",
        "MPBR11",
        "MPFI11",
        "MPFR11",
        "MPTECH",
        "MPGLOBAL",
    }
    assert all(item.canonical_id.startswith("demo.") for item in first.instruments)
    assert all(item.exchange == "DEMO" for item in first.instruments)
    assert all(
        item.data_support_status is DataSupportStatus.METADATA_ONLY for item in first.instruments
    )


def test_history_has_valid_decimal_ohlc_and_historical_demo_provenance():
    from app.demo.dataset import build_demo_dataset

    dataset = build_demo_dataset()
    daily = dataset.daily_bars
    intraday = dataset.intraday_bars
    dates = sorted({item.bar.timestamp.date() for item in daily})
    assert dates[0].isoformat() == "2025-01-01"
    assert dates[-1].isoformat() == "2026-01-30"
    assert (dates[-1] - dates[0]).days > 365
    assert len(daily) == len(dates) * 11
    assert {item.bar.timestamp.date() for item in intraday} == set(dates[-5:])
    assert len(intraday) == 11 * 5 * 7
    identities = set()
    for item in (*daily, *intraday):
        bar, provenance = item.bar, item.provenance
        assert UUID(item.id).version == 5
        assert (bar.canonical_id, item.interval, bar.timestamp) not in identities
        identities.add((bar.canonical_id, item.interval, bar.timestamp))
        assert bar.timestamp.weekday() < 5
        assert bar.timestamp.tzinfo is timezone.utc
        assert bar.timestamp <= dataset.cutoff
        assert all(
            isinstance(value, Decimal) and value.is_finite()
            for value in (bar.open, bar.high, bar.low, bar.close, bar.volume)
        )
        assert 0 < bar.low <= bar.open <= bar.high
        assert bar.low <= bar.close <= bar.high
        assert bar.volume >= 0
        assert bar.currency == "BRL"
        assert bar.adjustment_type is AdjustmentType.UNADJUSTED
        assert provenance.data_level is DataLevel.DEMO
        assert provenance.freshness is Freshness.STALE
        assert provenance.provider == "demo"
        assert provenance.source_timestamp == bar.timestamp
        assert provenance.collected_at == dataset.cutoff
        assert provenance.latency_ms is None
        assert provenance.source and provenance.dataset and provenance.limitations
    closes = {(item.bar.canonical_id, item.bar.timestamp): item.bar.close for item in daily}
    for item in intraday:
        if item.bar.timestamp.hour == 20:
            assert item.bar.close == closes[item.bar.canonical_id, item.bar.timestamp]


def test_personas_and_private_collection_plans_have_disjoint_stable_ids():
    from app.demo.dataset import build_demo_dataset

    dataset = build_demo_dataset()
    assert [user.email for user in dataset.users] == [
        "demo.a@market-pulse.local",
        "demo.b@market-pulse.local",
    ]
    assert [item.name for item in dataset.watchlists] == ["Growth Demo", "Income Demo"]
    assert [item.name for item in dataset.portfolios] == ["Alpha Demo", "Defensive Demo"]
    assert {item.owner_key for item in dataset.portfolios} == {"A", "B"}
    ids = [
        item.id
        for item in (
            *dataset.users,
            *dataset.watchlists,
            *dataset.portfolios,
            *dataset.favorites,
            *dataset.editorial_drafts,
        )
    ]
    ids += [event.id for portfolio in dataset.portfolios for event in portfolio.events]
    assert len(ids) == len(set(ids))
    assert all(UUID(item).version == 5 for item in ids)
    instruments = {item.canonical_id for item in dataset.instruments}
    assert all(set(item.canonical_ids) <= instruments for item in dataset.watchlists)
    assert all(item.canonical_id in instruments for item in dataset.favorites)


@pytest.mark.parametrize(
    "owner,cash,cost,value,realized,unrealized",
    [("A", "8020", "1990", "10100", "20", "90"), ("B", "3185", "1610", "4905", "0", "110")],
)
def test_portfolios_replay_and_value_at_generated_closes(
    owner,
    cash,
    cost,
    value,
    realized,
    unrealized,
):
    from app.demo.dataset import build_demo_dataset

    dataset = build_demo_dataset()
    portfolio = next(item for item in dataset.portfolios if item.owner_key == owner)
    prices = {}
    closes = {}
    for item in dataset.daily_bars:
        bar, provenance = item.bar, item.provenance
        closes[bar.canonical_id, bar.timestamp] = bar.close
        prices[bar.canonical_id] = PriceMark(
            canonical_id=bar.canonical_id,
            value=bar.close,
            currency=bar.currency,
            provider=provenance.provider,
            dataset=provenance.dataset,
            data_level=provenance.data_level,
            freshness=provenance.freshness,
            source_timestamp=provenance.source_timestamp,
            collected_at=provenance.collected_at,
            limitations=provenance.limitations,
        )
    for event in portfolio.events:
        assert event.notes and "DEMO" in event.notes
        if event.event_type in {"BUY", "SELL"}:
            assert event.unit_price == closes[event.canonical_id, event.occurred_at]
            assert event.gross_amount == event.quantity * event.unit_price
            assert event.fee_amount is None
        if event.event_type == "FEE":
            assert event.canonical_id is not None
        assert event.event_type not in {"DIVIDEND", "SPLIT", "ADJUSTMENT"}
    events = list(portfolio.events)
    state = replay_events(events)
    assert state.cash_balances == {"BRL": Decimal(cash)}
    assert sum(item.total_cost for item in state.positions.values()) == Decimal(cost)
    valuation = calculate_valuation(events, base_currency="BRL", prices=prices, fx_rates={})
    assert valuation.cash_value_base == Decimal(cash)
    assert valuation.total_value_base == Decimal(value)
    assert valuation.realized_pnl == Decimal(realized)
    assert valuation.unrealized_pnl == Decimal(unrealized)
    assert valuation.status == "COMPLETE"
    assert valuation.missing_inputs == ()


def test_corporate_actions_are_normalized_but_not_applied_to_ledgers():
    from app.demo.dataset import build_demo_dataset

    dataset = build_demo_dataset()
    assert Counter(item.action.action_type for item in dataset.corporate_actions) == {
        "CASH_DIVIDEND": 2,
        "JCP": 1,
        "SPLIT": 1,
    }
    for item in dataset.corporate_actions:
        action = item.action
        assert UUID(action.event_id).version == 5
        assert action.provider == "demo"
        assert action.instrument_id.startswith("demo.")
        assert action.status == "CONFIRMED"
        assert action.source_timestamp == item.provenance.source_timestamp
        assert item.provenance.data_level is DataLevel.DEMO
        assert item.provenance.freshness is Freshness.STALE
        assert action.collected_at == dataset.cutoff
    assert dataset.corporate_actions[2].action.net_amount_per_share == Decimal("0.425")
    assert dataset.corporate_actions[3].action.split_ratio_to == Decimal("2")
    assert dataset.corporate_actions[3].action.effective_date > dataset.cutoff.date()
    assert all(
        event.event_type not in {"DIVIDEND", "SPLIT", "ADJUSTMENT"}
        for portfolio in dataset.portfolios
        for event in portfolio.events
    )


def test_morning_calls_are_factual_attributed_validated_unpublished_drafts():
    from app.demo.dataset import build_demo_dataset

    dataset = build_demo_dataset()
    assert len(dataset.editorial_drafts) == 3
    for item in dataset.editorial_drafts:
        assert item.status is EditorialStatus.DRAFT
        assert "DEMO" in item.request.title
        assert validate_editorial_blocks(item.request.blocks).valid
        assert item.provenance.data_level is DataLevel.DEMO
        assert item.provenance.freshness is Freshness.STALE
        assert len(item.request.blocks) == 11
        assert "Não constitui recomendação de investimento" in item.request.blocks[-1].text
        for block in item.request.blocks:
            assert block.sources
            assert all(
                source.retrieved_at and source.justification and not source.url
                for source in block.sources
            )


def test_manifest_changes_when_financial_content_identity_or_timestamp_changes():
    from app.demo.dataset import build_demo_dataset

    dataset = build_demo_dataset()
    first = dataset.daily_bars[0]
    mutations = (
        replace(first, bar=replace(first.bar, close=first.bar.close + Decimal("0.01"))),
        replace(first, id="00000000-0000-5000-8000-000000000001"),
        replace(first, bar=replace(first.bar, timestamp=first.bar.timestamp + timedelta(hours=1))),
    )
    for mutated in mutations:
        changed = replace(dataset, daily_bars=(mutated, *dataset.daily_bars[1:]))
        assert changed.fingerprint() != dataset.fingerprint()
    summary = dataset.summary()
    assert summary["instruments"] == 11
    assert summary["portfolios"] == 2
    assert summary["editorial_drafts"] == 3
    assert summary["fingerprint"] == dataset.fingerprint()
    assert all("@" not in str(value) for value in summary.values())
    assert not any(isinstance(value, Decimal) for value in summary.values())


def test_daily_bars_aggregate_available_intraday_ohlcv():
    from app.demo.dataset import build_demo_dataset

    scenario = build_demo_dataset()
    for daily in scenario.daily_bars:
        hours = [
            item.bar
            for item in scenario.intraday_bars
            if item.bar.canonical_id == daily.bar.canonical_id
            and item.bar.timestamp.date() == daily.bar.timestamp.date()
        ]
        if hours:
            assert daily.bar.open == hours[0].open
            assert daily.bar.close == hours[-1].close
            assert daily.bar.high == max(item.high for item in hours)
            assert daily.bar.low == min(item.low for item in hours)
            assert daily.bar.volume == sum(item.volume for item in hours)


def test_scenario_has_distinct_trends_and_a_real_reversal_pair():
    from app.demo.dataset import build_demo_dataset

    scenario = build_demo_dataset()
    prices = {
        symbol: [
            item.bar.close for item in scenario.daily_bars if item.bar.canonical_id.endswith(symbol)
        ]
        for symbol in ("mpxa3", "mpxb3", "mpxc3", "mpxd3", "mpxe3")
    }
    assert prices["mpxa3"][-1] > prices["mpxa3"][0]
    assert prices["mpxb3"][-1] < prices["mpxb3"][0]
    assert max(prices["mpxc3"]) - min(prices["mpxc3"]) <= Decimal("2")
    assert max(prices["mpxd3"]) - min(prices["mpxd3"]) >= Decimal("15")
    recovery = prices["mpxe3"]
    assert min(recovery) < recovery[0] * Decimal("0.8")
    assert recovery[-1] > min(recovery) * Decimal("1.3")
    events = scenario.portfolios[1].events
    reversal = next(item for item in events if item.event_type == "REVERSAL")
    assert reversal.reversal_of_event_id in {item.id for item in events}
