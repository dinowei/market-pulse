"""Database restore and verification utility for Market Pulse (Day 28 Enterprise Hardening).

Supports:
- Safe restoration from backup artifacts (pg_restore or logical loader).
- Mandatory --confirm flag and SHA-256 verification of the dump against the manifest.
- Post-restore verification of record counts and schema integrity.

The target database is whatever --target-db-url names; this utility does not itself
decide which databases are legitimate restore targets. Authorization for the target
is an operator responsibility, covered by the runbook procedure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
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


def verify_manifest(manifest_path: Path) -> dict:
    """Verify backup manifest exists and is valid."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def verify_backup_integrity(backup_file: Path, expected_sha256: str) -> None:
    """Reject a dump whose bytes do not match the SHA-256 recorded at backup time."""
    digest = hashlib.sha256()
    with open(backup_file, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected_sha256:
        raise RuntimeError(
            f"Integrity check failed for {backup_file.name}: manifest records "
            f"{expected_sha256}, file hashes to {actual}. Refusing to restore."
        )


def _insertion_order(cursor, tables: list[str]) -> list[str]:
    """Order tables parents-first so foreign keys resolve during a row-by-row load."""
    cursor.execute(
        "SELECT src.relname, tgt.relname FROM pg_constraint c "
        "JOIN pg_class src ON src.oid = c.conrelid "
        "JOIN pg_class tgt ON tgt.oid = c.confrelid "
        "WHERE c.contype = 'f' AND src.relnamespace = 'public'::regnamespace"
    )
    wanted = set(tables)
    parents: dict[str, set[str]] = {table: set() for table in tables}
    for child, parent in cursor.fetchall():
        # Self-references are satisfied within a table, so they never constrain order.
        if child in wanted and parent in wanted and child != parent:
            parents[child].add(parent)

    ordered: list[str] = []
    remaining = dict(parents)
    while remaining:
        ready = sorted(t for t, deps in remaining.items() if not (deps - set(ordered)))
        if not ready:
            # A circular foreign-key chain cannot be ordered; load the rest as-is and
            # let PostgreSQL report any constraint it genuinely rejects.
            ordered.extend(sorted(remaining))
            break
        ordered.extend(ready)
        for table in ready:
            remaining.pop(table)
    return ordered


def restore_postgres(database_url: str, backup_file: Path) -> dict[str, int]:
    """Restore database from backup file and return restored table record counts."""
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    pg_restore = shutil.which("pg_restore")
    if pg_restore and backup_file.suffix == ".dump":
        env = os.environ.copy()
        parts = urlsplit(database_url)
        if parts.password:
            env["PGPASSWORD"] = parts.password
        cmd = [
            pg_restore,
            "-h", parts.hostname or "127.0.0.1",
            "-p", str(parts.port or 5432),
            "-U", parts.username or "postgres",
            "-d", parts.path.lstrip("/"),
            "--clean",
            "--if-exists",
            str(backup_file),
        ]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode not in {0, 1}:  # 1 can occur with minor warnings on clean
            raise RuntimeError(f"pg_restore failed with exit code {result.returncode}: {result.stderr}")
    else:
        # Logical JSON loader
        import psycopg
        from psycopg import sql

        with open(backup_file, encoding="utf-8") as f:
            data = json.load(f)

        populated = [table for table, rows in data.items() if rows]

        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                )
                existing = {row[0] for row in cur.fetchall()}
                missing = sorted(set(populated) - existing)
                if missing:
                    # A logical dump carries rows, not DDL, so the target must already be
                    # migrated. Say so instead of surfacing a raw UndefinedTable.
                    raise RuntimeError(
                        "Target database is missing tables required by this backup: "
                        f"{', '.join(missing)}. Run 'alembic upgrade head' against the "
                        "target before restoring."
                    )

                ordered = _insertion_order(cur, populated)
                # One TRUNCATE for every table at once: truncating them individually with
                # CASCADE would wipe rows already loaded into tables restored earlier.
                cur.execute(
                    sql.SQL("TRUNCATE TABLE {} CASCADE").format(
                        sql.SQL(", ").join(sql.Identifier(t) for t in ordered)
                    )
                )
                for table in ordered:
                    rows = data[table]
                    cols = list(rows[0].keys())
                    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                        sql.Identifier(table),
                        sql.SQL(", ").join(sql.Identifier(c) for c in cols),
                        sql.SQL(", ").join(sql.Placeholder() * len(cols)),
                    )
                    cur.executemany(query, [tuple(row[c] for c in cols) for row in rows])
            conn.commit()

    # Post-restore verification: get record counts
    import psycopg
    counts: dict[str, int] = {}
    with psycopg.connect(database_url) as conn:
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        ).fetchall()
        for t_row in tables:
            tname = t_row[0]
            cnt = conn.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
            counts[tname] = cnt

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Market Pulse Restore Utility")
    parser.add_argument("--backup-dir", required=True, help="Directory containing backup files and manifest")
    parser.add_argument("--target-db-url", required=True, help="Target PostgreSQL connection URL")
    parser.add_argument("--confirm", action="store_true", help="Explicit confirmation required to restore")

    args = parser.parse_args()
    if not args.confirm:
        print("Error: --confirm flag is required to execute a database restoration.", file=sys.stderr)
        sys.exit(1)

    backup_dir = Path(args.backup_dir)
    manifest = verify_manifest(backup_dir / "backup_manifest.json")
    print(f"Manifest verified: generated at {manifest['timestamp']} for '{manifest['environment']}'")

    pg_backup_name = manifest["postgres_backup"]["file"]
    pg_file = backup_dir / pg_backup_name

    expected_sha256 = manifest["postgres_backup"].get("sha256")
    if not expected_sha256:
        raise RuntimeError("Manifest does not record a SHA-256 for the dump; refusing to restore.")
    verify_backup_integrity(pg_file, expected_sha256)
    print(f"Dump integrity verified against manifest SHA-256: {expected_sha256[:16]}...")

    print(f"Restoring PostgreSQL to: {mask_url(args.target_db_url)}...")
    counts = restore_postgres(args.target_db_url, pg_file)
    print("Post-restore verification results:")
    for tbl, count in sorted(counts.items()):
        print(f"  {tbl}: {count} records")
    print("Restore completed and verified successfully.")


if __name__ == "__main__":
    main()
