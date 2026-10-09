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
    # The rediss scheme is Redis over TLS (managed services require it), and the user part
    # of the authority may be empty (only a colon before the password), so both are matched.
    re.compile(
        r"(?i)(?:postgres(?:ql)?|rediss?)://[^\s/:]*:(?P<password>[^\s/@]+)@"
    ),
    re.compile(
        r"(?i)\b(?:BRAPI_API_TOKEN|HG_BRASIL_API_KEY|TWELVE_DATA_API_KEY|"
        r"ALPHA_VANTAGE_API_KEY|OPEN_EXCHANGE_RATES_APP_ID|MASSIVE_API_KEY|"
        r"B3_DEVELOPERS_CLIENT_ID)[ \t]*[:=][ \t]*['\"]?(?P<provider_value>[^\s'\"]{8,})"
    ),
)
# Only complete, explicit placeholders are exempt. A marker inside a token or
# password must never suppress a finding (and an empty marker matches everything).
LOCAL_PASSWORD_PLACEHOLDERS = frozenset({"local_only", "market_pulse_local_only"})
PROVIDER_PLACEHOLDERS = frozenset(
    {"local_only", "YOUR_TOKEN", "YOUR_API_KEY", "SEU_TOKEN", "SEU_API_KEY"}
)
WORKFLOW_ACTION_RE = re.compile(r"^\s*-\s*uses:\s*(?P<reference>[^#\s]+)", re.MULTILINE)


def files() -> list[Path]:
    candidates = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\0")
    paths = {ROOT / item for item in candidates if item}
    paths.add(Path(__file__).resolve())
    return sorted(path for path in paths if path.is_file())


def secret_scan() -> int:
    failures: list[str] = []
    for path in files():
        if path.suffix.lower() not in {".md", ".py", ".ts", ".tsx", ".json", ".yml", ".yaml", ".env", ".example"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                fields = match.groupdict()
                if fields.get("password") in LOCAL_PASSWORD_PLACEHOLDERS:
                    continue
                if fields.get("provider_value") in PROVIDER_PLACEHOLDERS:
                    continue
                failures.append(f"{path.relative_to(ROOT)}:{match.start() + 1}")
    if failures:
        print("Potential secret patterns:", *failures, sep="\n")
        return 1
    print("SECRET_SCAN=PASS")
    return 0


def workflow_security_failures() -> list[str]:
    failures: list[str] = []
    workflow_dir = ROOT / ".github" / "workflows"
    for path in sorted((*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml"))):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            match = WORKFLOW_ACTION_RE.match(line)
            if not match:
                continue
            reference = match.group("reference")
            location = f"{path.relative_to(ROOT)}:{index + 1}"
            if not reference.startswith("./") and not re.fullmatch(
                r"[^@]+@[0-9a-f]{40}", reference, flags=re.IGNORECASE
            ):
                failures.append(f"{location}: action must use a full commit SHA")
            if reference.casefold().startswith("actions/checkout@"):
                step_indent = len(line) - len(line.lstrip())
                block = []
                for following in lines[index + 1 :]:
                    following_indent = len(following) - len(following.lstrip())
                    if following.strip() and following_indent <= step_indent:
                        break
                    block.append(following)
                credentials_disabled = any(
                    re.fullmatch(r"\s*persist-credentials:\s*false\s*", item)
                    for item in block
                )
                if not credentials_disabled:
                    failures.append(f"{location}: checkout must disable persisted credentials")
    return failures


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
    workflow_failures = workflow_security_failures()
    if workflow_failures:
        print("Workflow security gate failed:", *workflow_failures, sep="\n")
        return 1
    print("YFINANCE=ABSENT")
    print("LOCKFILES=PASS")
    print("ACTIONS_PINNED_TO_SHA=PASS")
    print("CHECKOUT_CREDENTIALS=NOT_PERSISTED")
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
