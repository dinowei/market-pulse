#!/usr/bin/env python3
"""Compliance gate for the Dia 26 public contracts."""

from __future__ import annotations

import io
import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))


def main() -> int:
    from app.contracts import DataLevel
    from app.market_data.benchmarks import benchmark_items
    from app.market_data.economic_calendar import demo_events, validate_calendar_event

    modules = (
        API / "app" / "market_data" / "comparison.py",
        API / "app" / "market_data" / "economic_calendar.py",
        API / "app" / "market_data" / "benchmarks.py",
    )
    float_tokens = re.compile(r"\b(?:FLOAT|REAL|DOUBLE\s+PRECISION)\b", re.IGNORECASE)

    def code_only(path: Path) -> str:
        source = path.read_text(encoding="utf-8")
        kept: list[str] = []
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type not in {tokenize.STRING, tokenize.COMMENT}:
                kept.append(token.string)
        return " ".join(kept)

    violations = [
        f"{path.relative_to(ROOT)}: financial floating-point token"
        for path in modules
        if float_tokens.search(code_only(path))
    ]
    if violations:
        print("FLOAT_GATE=FAIL")
        print("\n".join(violations))
        return 1

    events = demo_events()
    if not events or not all(validate_calendar_event(event) for event in events):
        print("CALENDAR_LEXICAL_GATE=FAIL")
        return 1
    if any(event.provenance.data_level is not DataLevel.DEMO for event in events):
        print("CALENDAR_DEFAULT_DENY=FAIL")
        return 1

    benchmarks = benchmark_items()
    if not benchmarks or any(item.data_level is not DataLevel.DEMO for item in benchmarks):
        print("BENCHMARK_DEFAULT_DENY=FAIL")
        return 1

    print("FLOAT_GATE=PASS")
    print("CALENDAR_LEXICAL_GATE=PASS")
    print("CALENDAR_DEFAULT_DENY=PASS")
    print("BENCHMARK_DEFAULT_DENY=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
