"""Decimal-only transforms for multi-series comparison."""

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

INDEX_QUANTUM = Decimal("0.0001")


def normalize_index_100(values: Sequence[Decimal | None]) -> list[Decimal | None]:
    """Rebase the first available value to 100 without float conversion."""
    base = next((value for value in values if value is not None), None)
    if base is None or base == 0:
        return [None for _ in values]
    return [
        None
        if value is None
        else (value / base * Decimal("100")).quantize(
            INDEX_QUANTUM, rounding=ROUND_HALF_UP
        )
        for value in values
    ]
