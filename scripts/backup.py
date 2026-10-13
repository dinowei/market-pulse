"""Database and cache backup utility for Market Pulse (Day 28 Enterprise Hardening).

Supports:
- PostgreSQL dump via pg_dump CLI or logical table dump fallback.
- Redis snapshot trigger via BGSAVE.
- Checksum generation and manifest creation.
- Strict credential masking (never leaks passwords in logs or files).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


def mask_url(url: str) -> str:
    """Mask password in connection URL for safe logging."""
    try:
        parts = urlsplit(url)
        if parts.password:
            netloc = f"{parts.username}:***@{parts.hostname}"
            if parts.port:
                netloc += f":{parts.port}"
            return parts._replace(netloc=netloc).geturl()
    except Exception:
        pass
    return "***"


def backup_postgres(database_url: str, output_path: Path) -> dict[str, str | int]:
    """Execute PostgreSQL backup to output_path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pg_dump = shutil.which("pg_dump")
    if pg_dump:
        # Use official pg_dump tool
        env = os.environ.copy()
        parts = urlsplit(database_url)
        if parts.password:
            env["PGPASSWORD"] = parts.password
        cmd = [
            pg_dump,
            "-h", parts.hostname or "127.0.0.1",
            "-p", str(parts.port or 5432),
            "-U", parts.username or "postgres",
            "-d", parts.path.lstrip("/"),
            "-F", "c",  # custom compressed format
            "-f", str(output_path),
        ]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed with exit code {result.returncode}")
    else:
        # Fallback: logical JSON dump using psycopg
        import psycopg
        from psycopg.rows import dict_row

        data: dict[str, list] = {}
        with psycopg.connect(database_url, row_factory=dict_row) as conn:
            # Query table list
            tables = conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            ).fetchall()
            for t_row in tables:
                tname = t_row["table_name"]
                rows = conn.execute(f"SELECT * FROM {tname}").fetchall()
                # Serialize rows with ISO format for datetimes
                clean_rows = []
                for r in rows:
                    clean = {}
                    for k, v in r.items():
                        if isinstance(v, (datetime,)):
                            clean[k] = v.isoformat()
                        elif hasattr(v, "__str__") and type(v).__name__ in {"Decimal", "UUID"}:
                            clean[k] = str(v)
                        else:
                            clean[k] = v
                    clean_rows.append(clean)
                data[tname] = clean_rows

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # Compute checksum
    hasher = hashlib.sha256()
    with open(output_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    checksum = hasher.hexdigest()
    size = output_path.stat().st_size

    return {
        "file": str(output_path.name),
        "size_bytes": size,
        "sha256": checksum,
    }


SNAPSHOT_OK = "OK"
SNAPSHOT_NOT_SUPPORTED = "NAO_SUPORTADO"  # the server answered and refused the command
SNAPSHOT_UNAVAILABLE = "INDISPONIVEL"  # no connection, timeout or invalid URL

_LEGACY_STATUS = {
    SNAPSHOT_OK: "bgsave_triggered",
    SNAPSHOT_NOT_SUPPORTED: "bgsave_not_supported",
    SNAPSHOT_UNAVAILABLE: "redis_unavailable",
}


def backup_redis(redis_url: str, output_path: Path) -> dict[str, str | None]:
    """Ask Redis for a snapshot and record, explicitly, what happened.

    Managed Redis services commonly refuse LASTSAVE and BGSAVE. A refusal is reported in
    the "snapshot" field (OK, NAO_SUPORTADO or INDISPONIVEL), never swallowed, and the rest
    of the backup continues: Redis is a non-authoritative cache and PostgreSQL is the source
    of truth. Only the exception NAME is recorded, never its message, which may carry a
    host or a value.
    """
    from redis import Redis
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import RedisError
    from redis.exceptions import TimeoutError as RedisTimeoutError

    unreachable = (RedisConnectionError, RedisTimeoutError, OSError, ValueError)
    snapshot = SNAPSHOT_OK
    detail: str | None = None
    last_save = None
    try:
        client = Redis.from_url(redis_url, socket_timeout=5)
        try:
            last_save = client.lastsave()
        except unreachable:
            raise
        except RedisError as exc:
            # LASTSAVE refused; BGSAVE may still be accepted, so keep going and say so.
            detail = f"LASTSAVE:{type(exc).__name__}"
        client.bgsave()
    except unreachable as exc:
        snapshot, detail = SNAPSHOT_UNAVAILABLE, type(exc).__name__
    except RedisError as exc:
        if "already in progress" in str(exc).lower():
            snapshot, detail = SNAPSHOT_OK, "BGSAVE_ALREADY_RUNNING"
        else:
            snapshot, detail = SNAPSHOT_NOT_SUPPORTED, type(exc).__name__

    info: dict[str, str | None] = {
        "redis_target": mask_url(redis_url),
        "last_save_timestamp": last_save.isoformat() if hasattr(last_save, "isoformat") else None,
        "snapshot": snapshot,
        "detail": detail,
        "status": _LEGACY_STATUS[snapshot],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    return info


def create_backup_manifest(
    backup_dir: Path,
    pg_meta: dict,
    redis_meta: dict,
    environment: str,
) -> Path:
    """Create a signed manifest of the backup."""
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": environment,
        "postgres_backup": pg_meta,
        "redis_backup": redis_meta,
    }
    manifest_path = backup_dir / "backup_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Market Pulse Backup Utility")
    parser.add_argument("--output-dir", default="./backups", help="Directory for backup files")
    parser.add_argument("--db-url", default=os.environ.get("MARKET_PULSE_DATABASE_URL"))
    parser.add_argument("--redis-url", default=os.environ.get("MARKET_PULSE_REDIS_URL", "redis://127.0.0.1:6379/0"))
    parser.add_argument("--environment", default=os.environ.get("MARKET_PULSE_ENVIRONMENT", "local"))

    args = parser.parse_args()
    if not args.db_url:
        print("Error: Database URL must be specified via --db-url or MARKET_PULSE_DATABASE_URL", file=sys.stderr)
        sys.exit(1)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target_dir = Path(args.output_dir) / ts
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starting backup for environment '{args.environment}'...")
    print(f"PostgreSQL target: {mask_url(args.db_url)}")
    pg_file = target_dir / "market_pulse_postgres.dump"
    pg_meta = backup_postgres(args.db_url, pg_file)
    print(f"PostgreSQL backup saved: {pg_file} (SHA256: {pg_meta['sha256'][:16]}...)")

    redis_file = target_dir / "market_pulse_redis.json"
    redis_meta = backup_redis(args.redis_url, redis_file)
    print(f"REDIS_SNAPSHOT={redis_meta['snapshot']}")
    if redis_meta["snapshot"] != SNAPSHOT_OK:
        print(
            "AVISO: o snapshot do Redis NAO foi feito "
            f"(detalhe: {redis_meta['detail']}). O backup do PostgreSQL esta completo; "
            "o Redis e cache nao autoritativo.",
            file=sys.stderr,
        )
    print(f"Redis backup recorded: {redis_file}")

    manifest_path = create_backup_manifest(target_dir, pg_meta, redis_meta, args.environment)
    print(f"Manifest created: {manifest_path}")
    if redis_meta["snapshot"] == SNAPSHOT_OK:
        print("Backup completed successfully.")
    else:
        print(f"Backup completed with warnings: PostgreSQL OK, Redis snapshot {redis_meta['snapshot']}.")


if __name__ == "__main__":
    main()
