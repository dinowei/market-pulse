#!/usr/bin/env python3
"""Small, dependency-free checks shared by local runs and CI."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = (
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:sk_live|rk_live|ghp_|github_pat_)[A-Za-z0-9_\-]+\b"),
    re.compile(r"(?i)(?:postgres(?:ql)?|redis)://[^\s/:]+:[^\s/@]+@"),
    re.compile(
        r"(?i)\b(?:BRAPI_API_TOKEN|HG_BRASIL_API_KEY|TWELVE_DATA_API_KEY|"
        r"ALPHA_VANTAGE_API_KEY|OPEN_EXCHANGE_RATES_APP_ID|MASSIVE_API_KEY|"
        r"B3_DEVELOPERS_CLIENT_ID)\s*[:=]\s*['\"]?[^\s'\"]{8,}"
    ),
)
ALLOWED_DEMO = ("local_only", "", "YOUR_", "SEU_", "example", "demo")


def files() -> list[Path]:
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    paths = {ROOT / item for item in tracked}
    paths.add(Path(__file__).resolve())
    return [path for path in paths if path.is_file()]


def secret_scan() -> int:
    failures: list[str] = []
    for path in files():
        if path.suffix.lower() not in {".md", ".py", ".ts", ".tsx", ".json", ".yml", ".yaml", ".env", ".example"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(0)
                if any(marker in value for marker in ALLOWED_DEMO):
                    continue
                failures.append(f"{path.relative_to(ROOT)}:{match.start() + 1}")
    if failures:
        print("Potential secret patterns:", *failures, sep="\n")
        return 1
    print("SECRET_SCAN=PASS")
    return 0


def supply_chain() -> int:
    required = ("pnpm-lock.yaml", "apps/api/uv.lock", "apps/web/package.json")
    missing = [item for item in required if not (ROOT / item).is_file()]
    if missing:
        print("Missing lock/manifests:", ", ".join(missing))
        return 1
    yfinance_locations: list[str] = []
    scan_paths = [
        path
        for path in (ROOT / "pyproject.toml", ROOT / "apps/api/pyproject.toml", ROOT / "apps/api/uv.lock")
        if path.is_file()
    ]
    scan_paths += [path for path in (ROOT / "apps/api/app").rglob("*.py") if path.is_file()]
    for path in scan_paths:
        if "yfinance" in path.read_text(encoding="utf-8", errors="ignore").casefold():
            yfinance_locations.append(str(path.relative_to(ROOT)))
    if yfinance_locations:
        print("yfinance found:", ", ".join(yfinance_locations))
        return 1
    print("YFINANCE=ABSENT")
    print("LOCKFILES=PASS")
    print("LICENSES=MANUAL_REVIEW_REQUIRED (no license database is bundled)")
    print("VULNERABILITIES=RUN pnpm audit and review uv audit tooling before release")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=("secrets", "supply-chain"))
    args = parser.parse_args()
    return secret_scan() if args.check == "secrets" else supply_chain()


if __name__ == "__main__":
    sys.exit(main())
