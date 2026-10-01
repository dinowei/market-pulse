"""scripts/backup.py must say so, loudly, when Redis refuses or misses the snapshot.

A managed Redis commonly refuses LASTSAVE and BGSAVE. The refusal used to be swallowed
and the manifest still claimed the snapshot was triggered. No Redis is needed here:
redis.Redis.from_url is replaced by a fake that refuses on demand.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError
from redis.exceptions import TimeoutError as RedisTimeoutError

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import backup  # noqa: E402

LEAKY = "SECRET_MESSAGE_TEXT host.internal.invalid"
LOCAL_DB = "postgresql://market_pulse:local_only@127.0.0.1:5432/market_pulse"


class _FakeClient:
    def __init__(self, lastsave=None, bgsave=None) -> None:
        self._lastsave, self._bgsave = lastsave, bgsave

    def _run(self, behaviour):
        if isinstance(behaviour, Exception):
            raise behaviour
        return behaviour

    def lastsave(self):
        return self._run(self._lastsave)

    def bgsave(self):
        return self._run(self._bgsave)


def _install(monkeypatch, client: _FakeClient) -> None:
    monkeypatch.setattr("redis.Redis.from_url", lambda *_a, **_k: client)


def _recorded(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_a_refusing_server_is_reported_not_swallowed(monkeypatch, tmp_path) -> None:
    refusal = ResponseError("ERR unknown command 'BGSAVE' " + LEAKY)
    _install(monkeypatch, _FakeClient(lastsave=refusal, bgsave=refusal))
    target = tmp_path / "redis.json"

    info = backup.backup_redis("redis://127.0.0.1:6379/0", target)

    assert info["snapshot"] == "NAO_SUPORTADO"
    assert info["status"] != "bgsave_triggered", "the manifest must not claim a snapshot was taken"
    assert _recorded(target) == info
    assert "SECRET_MESSAGE_TEXT" not in json.dumps(info), "the server message must not be recorded"
    assert info["detail"] == "LASTSAVE:ResponseError" or info["detail"] == "ResponseError"


def test_lastsave_refused_but_bgsave_accepted_still_counts_as_a_snapshot(
    monkeypatch, tmp_path
) -> None:
    _install(monkeypatch, _FakeClient(lastsave=ResponseError("ERR " + LEAKY), bgsave=True))

    info = backup.backup_redis("redis://127.0.0.1:6379/0", tmp_path / "redis.json")

    assert info["snapshot"] == "OK"
    assert info["last_save_timestamp"] is None
    assert info["detail"] == "LASTSAVE:ResponseError"


@pytest.mark.parametrize(
    "failure", [RedisConnectionError(LEAKY), RedisTimeoutError(LEAKY), OSError(LEAKY)]
)
def test_an_unreachable_redis_is_reported_and_does_not_abort(
    monkeypatch, tmp_path, failure
) -> None:
    _install(monkeypatch, _FakeClient(lastsave=failure))

    info = backup.backup_redis("redis://127.0.0.1:6379/0", tmp_path / "redis.json")

    assert info["snapshot"] == "INDISPONIVEL"
    assert "SECRET_MESSAGE_TEXT" not in json.dumps(info)


def test_a_snapshot_already_running_is_not_a_refusal(monkeypatch, tmp_path) -> None:
    running = ResponseError("ERR Background save already in progress")
    saved = datetime(2026, 10, 1, tzinfo=timezone.utc)
    _install(monkeypatch, _FakeClient(lastsave=saved, bgsave=running))

    info = backup.backup_redis("redis://127.0.0.1:6379/0", tmp_path / "redis.json")

    assert info["snapshot"] == "OK"
    assert info["detail"] == "BGSAVE_ALREADY_RUNNING"


def test_a_normal_snapshot_records_the_last_save_time(monkeypatch, tmp_path) -> None:
    saved = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    _install(monkeypatch, _FakeClient(lastsave=saved, bgsave=True))

    info = backup.backup_redis("redis://127.0.0.1:6379/0", tmp_path / "redis.json")

    assert info["snapshot"] == "OK"
    assert info["status"] == "bgsave_triggered"
    assert info["last_save_timestamp"] == saved.isoformat()
    assert info["detail"] is None


def test_the_command_line_says_so_and_still_writes_the_manifest(
    monkeypatch, tmp_path, capsys
) -> None:
    refusal = ResponseError("ERR unknown command 'BGSAVE' " + LEAKY)
    _install(monkeypatch, _FakeClient(lastsave=refusal, bgsave=refusal))

    def fake_postgres(_url: str, output_path: Path) -> dict:
        output_path.write_bytes(b"synthetic dump")
        return {"file": output_path.name, "size_bytes": 14, "sha256": "0" * 64}

    monkeypatch.setattr(backup, "backup_postgres", fake_postgres)
    monkeypatch.setattr(
        sys,
        "argv",
        ["backup.py", "--output-dir", str(tmp_path), "--db-url", LOCAL_DB,
         "--redis-url", "redis://127.0.0.1:6379/0", "--environment", "local"],
    )

    backup.main()  # must not raise or exit non-zero: the PostgreSQL backup is complete

    captured = capsys.readouterr()
    assert "REDIS_SNAPSHOT=NAO_SUPORTADO" in captured.out
    assert "AVISO" in captured.err
    assert "Backup completed with warnings" in captured.out
    assert "Backup completed successfully" not in captured.out
    assert "SECRET_MESSAGE_TEXT" not in captured.out + captured.err

    manifest = _recorded(next(tmp_path.glob("*/backup_manifest.json")))
    assert manifest["postgres_backup"]["sha256"] == "0" * 64
    assert manifest["redis_backup"]["snapshot"] == "NAO_SUPORTADO"


def test_the_command_line_stays_quiet_about_warnings_when_the_snapshot_works(
    monkeypatch, tmp_path, capsys
) -> None:
    saved = datetime(2026, 10, 1, tzinfo=timezone.utc)
    _install(monkeypatch, _FakeClient(lastsave=saved, bgsave=True))

    def fake_postgres(_url: str, path: Path) -> dict:
        path.write_bytes(b"x")
        return {"file": path.name, "size_bytes": 1, "sha256": "1" * 64}

    monkeypatch.setattr(backup, "backup_postgres", fake_postgres)
    monkeypatch.setattr(
        sys, "argv", ["backup.py", "--output-dir", str(tmp_path), "--db-url", LOCAL_DB]
    )

    backup.main()

    captured = capsys.readouterr()
    assert "REDIS_SNAPSHOT=OK" in captured.out
    assert "Backup completed successfully" in captured.out
    assert captured.err == ""
