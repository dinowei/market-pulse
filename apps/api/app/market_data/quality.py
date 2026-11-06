"""Series-level quality checks and cross-source comparison (ADR-025).

Bar-level rules (OHLC, positive prices, timezone) live in `normalization.MarketBar`. These
checks look across bars and across providers. They report; they never repair or pick a side.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.market_data.normalization import MarketBar
from app.providers.canonical import FUTURE_TOLERANCE, QualityStatus


@dataclass(frozen=True)
class SeriesIssue:
    code: str
    detail: str


@dataclass(frozen=True)
class SeriesQuality:
    status: QualityStatus
    issues: tuple[SeriesIssue, ...]


def check_series(
    bars: Sequence[MarketBar], *, now: datetime, expected_currency: str | None = None
) -> SeriesQuality:
    issues: list[SeriesIssue] = []
    seen: set[datetime] = set()
    for index, bar in enumerate(bars):
        if bar.timestamp in seen:
            issues.append(SeriesIssue("DUPLICATE_TIMESTAMP", bar.timestamp.isoformat()))
        seen.add(bar.timestamp)
        if index and bar.timestamp < bars[index - 1].timestamp:
            issues.append(SeriesIssue("OUT_OF_ORDER", bar.timestamp.isoformat()))
        if bar.timestamp > now + FUTURE_TOLERANCE:
            issues.append(SeriesIssue("FUTURE_TIMESTAMP", bar.timestamp.isoformat()))
    if len({bar.canonical_id for bar in bars}) > 1:
        issues.append(SeriesIssue("MIXED_INSTRUMENT", "mais de um canonical_id na série"))
    currencies = {bar.currency for bar in bars}
    if len(currencies) > 1:
        issues.append(SeriesIssue("MIXED_CURRENCY", ", ".join(sorted(currencies))))
    elif expected_currency and currencies and currencies != {expected_currency}:
        issues.append(
            SeriesIssue("CURRENCY_MISMATCH", f"{currencies.pop()} != {expected_currency}")
        )
    adjustments = {bar.adjustment_type.value for bar in bars}
    if len(adjustments) > 1:
        issues.append(SeriesIssue("MIXED_ADJUSTMENT", ", ".join(sorted(adjustments))))
    return SeriesQuality(
        QualityStatus.QUARANTINED if issues else QualityStatus.VALID, tuple(issues)
    )


@dataclass(frozen=True)
class SourceComparison:
    status: str
    difference_ratio: Decimal


def compare_sources(
    primary: Decimal, secondary: Decimal, *, tolerance_ratio: Decimal
) -> SourceComparison:
    """AGREE or DIVERGENT; the caller's precedence policy decides, nothing is averaged."""

    if primary <= 0 or secondary <= 0:
        raise ValueError("prices must be positive")
    if tolerance_ratio < 0:
        raise ValueError("tolerance cannot be negative")
    ratio = abs(primary - secondary) / primary
    return SourceComparison("DIVERGENT" if ratio > tolerance_ratio else "AGREE", ratio)
