"""Local, opt-in trigger for the protected refresh endpoint.

The script never embeds a URL or credential and defaults to a dry run.
"""

from __future__ import annotations

import argparse
import json
import os
from urllib.request import Request, urlopen


def build_payload(canonical_ids: list[str], *, mode: str = "DRY_RUN") -> dict[str, object]:
    if not canonical_ids or any("." not in value for value in canonical_ids):
        raise ValueError("explicit canonical_ids are required")
    if len(canonical_ids) > 100:
        raise ValueError("at most 100 instruments may be requested")
    if mode not in {"DRY_RUN", "DEMO_ONLY", "LICENSED_ONLY"}:
        raise ValueError("unsupported refresh mode")
    return {
        "dataset": "demo-quotes",
        "capability": "latest_quote",
        "canonical_ids": canonical_ids,
        "mode": mode,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("canonical_ids", nargs="+", help="canonical instrument identities")
    parser.add_argument("--mode", default="DRY_RUN", choices=["DRY_RUN", "DEMO_ONLY", "LICENSED_ONLY"])
    parser.add_argument("--execute", action="store_true", help="send the request; otherwise print payload only")
    args = parser.parse_args()
    payload = build_payload(args.canonical_ids, mode=args.mode)
    if not args.execute:
        print(json.dumps(payload, sort_keys=True))
        return 0
    base_url = os.environ.get("MARKET_PULSE_API_BASE_URL", "").rstrip("/")
    secret = os.environ.get("MARKET_PULSE_CRON_SECRET", "")
    if not base_url or not secret:
        parser.error("MARKET_PULSE_API_BASE_URL and MARKET_PULSE_CRON_SECRET are required for --execute")
    request = Request(
        f"{base_url}/api/v1/internal/refresh-quotes",
        data=json.dumps(payload).encode(),
        headers={"X-Cron-Secret": secret, "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - explicit operator-supplied URL
        print(response.read().decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
