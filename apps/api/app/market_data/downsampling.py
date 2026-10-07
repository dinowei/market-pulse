"""Display downsampling for historical series (Day 31, ADR-013).

M4 by index buckets: every bucket keeps its first, last, minimum and maximum point, and
every gap or valueless point is always kept. The output is an ordered subset of the input
points, so no value, timestamp or point is ever created, interpolated or rounded
(directive section 14; chart semantics "Regras anti-distorção").
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TypeVar

from app.contracts import PublicHistoryPoint

DOWNSAMPLING_METHOD = "M4"
MIN_MAX_POINTS = 64
MAX_MAX_POINTS = 5000

P = TypeVar("P", bound=PublicHistoryPoint)


@dataclass(frozen=True)
class Downsampled:
    points: list[PublicHistoryPoint]
    original_points: int
    applied: bool


def _value(point: PublicHistoryPoint) -> Decimal | None:
    return point.value if point.value is not None else point.close


def _is_structural(point: PublicHistoryPoint) -> bool:
    return point.is_gap or _value(point) is None


def downsample_m4(points: Sequence[P], max_points: int) -> Downsampled:
    """Reduce a series to at most ``max_points`` exact points plus every gap.

    Gaps and valueless points are structural (they show missing sessions), so they are
    always kept even if that exceeds ``max_points``; hiding a gap would draw a line across
    a period with no trading.
    """
    if not MIN_MAX_POINTS <= max_points <= MAX_MAX_POINTS:
        raise ValueError(f"max_points must be between {MIN_MAX_POINTS} and {MAX_MAX_POINTS}")
    original = len(points)
    if original <= max_points:
        return Downsampled(list(points), original, applied=False)

    keep: set[int] = {0, original - 1}
    keep.update(index for index, point in enumerate(points) if _is_structural(point))

    buckets = max(1, max_points // 4)
    for bucket in range(buckets):
        start = bucket * original // buckets
        end = (bucket + 1) * original // buckets
        valued = [index for index in range(start, end) if not _is_structural(points[index])]
        if not valued:
            continue
        keep.add(valued[0])
        keep.add(valued[-1])
        # Ties keep the earliest index so the result is deterministic.
        keep.add(min(valued, key=lambda index: (_value(points[index]), index)))
        keep.add(max(valued, key=lambda index: (_value(points[index]), -index)))

    return Downsampled([points[index] for index in sorted(keep)], original, applied=True)
