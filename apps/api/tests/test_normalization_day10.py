from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.market_data.normalization import (
    AdjustmentType,
    FxRate,
    MarketBar,
    OutlierPolicy,
    normalize_batch,
)
from app.market_data.persistence import PriceBarStore


def bar(close: str = "10", timestamp: str = "2026-09-01T12:00:00-03:00") -> dict[str, str]:
    return {
        "canonical_id": "equity.br.b3.petr4",
        "timestamp": timestamp,
        "open": "9",
        "high": "11",
        "low": "8",
        "close": close,
        "volume": "100",
        "currency": "BRL",
        "adjustment_type": "UNADJUSTED",
    }


def test_ohlc_invariants_and_utc_normalization() -> None:
    result = MarketBar.from_payload(bar())
    assert result.close == Decimal("10")
    assert result.timestamp.tzinfo is not None
    assert result.timestamp == datetime(2026, 9, 1, 15, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "field,value", [("low", "12"), ("open", "12"), ("close", "12"), ("close", "0")]
)
def test_invalid_ohlc_is_rejected(field: str, value: str) -> None:
    payload = bar()
    payload[field] = value
    with pytest.raises(ValueError):
        MarketBar.from_payload(payload)


def test_adjustment_type_is_explicit() -> None:
    assert MarketBar.from_payload(bar()).adjustment_type is AdjustmentType.UNADJUSTED
    with pytest.raises(ValueError):
        payload = bar()
        payload.pop("adjustment_type")
        MarketBar.from_payload(payload)


def test_batch_quarantines_bad_item_and_keeps_valid_item() -> None:
    result = normalize_batch(
        [bar(), {**bar("12"), "low": "20"}], OutlierPolicy(max_change_ratio=Decimal("0.5"))
    )
    assert len(result.accepted) == 1
    assert len(result.quarantined) == 1
    assert result.quarantined[0].reason == "INVALID_OHLC"


def test_fx_direction_and_positive_decimal_rate() -> None:
    fx = FxRate.from_payload(
        {
            "base_currency": "USD",
            "quote_currency": "BRL",
            "rate": "5.10",
            "timestamp": "2026-09-01T12:00:00Z",
        }
    )
    assert fx.base_currency == "USD"
    assert fx.quote_currency == "BRL"
    assert fx.rate == Decimal("5.10")
    with pytest.raises(ValueError):
        FxRate.from_payload(
            {
                "base_currency": "USD",
                "quote_currency": "BRL",
                "rate": "0",
                "timestamp": "2026-09-01T12:00:00Z",
            }
        )


def test_price_bar_upsert_is_idempotent_and_conflict_is_quarantined() -> None:
    store = PriceBarStore()
    item = MarketBar.from_payload(bar())
    assert store.upsert(item, provider="brapi", dataset="history") == "inserted"
    assert store.upsert(item, provider="brapi", dataset="history") == "unchanged"
    conflict = MarketBar.from_payload(bar("10.2"))
    assert store.upsert(conflict, provider="brapi", dataset="history") == "quarantined"
    assert len(store.items) == 1
