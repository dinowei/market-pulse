"""Print each provider credential's status, never its value (ADR-027).

    uv run python -m app.providers.credentials_report [--env-file .env]

Statuses: PRESENTE, AUSENTE, NÃO LIDA PELO CÓDIGO (an old name the code ignores). INVÁLIDA
needs a provider answer (401) and is shown in the internal panel of the running API.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from app.providers.registry import REGISTRY, credential_status


def _env_file(path: Path) -> dict[str, str]:
    """KEY=VALUE lines; values stay in memory and are never printed."""

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if text and not text.startswith("#") and "=" in text:
            key, value = text.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    return values


def report(environ: dict[str, str]) -> list[str]:
    lines = []
    for entry in REGISTRY:
        for name, status in credential_status(entry, environ).items():
            lines.append(f"{entry.provider_id:<20} {name:<30} {status.value}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env-file", type=Path, help="also read KEY=VALUE pairs from this file")
    args = parser.parse_args(argv)
    environ = dict(os.environ)
    if args.env_file:
        environ.update(_env_file(args.env_file))
    print("\n".join(report(environ)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
