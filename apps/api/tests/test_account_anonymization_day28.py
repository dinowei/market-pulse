"""Account anonymization: session revocation, rollback of the revocation marker, audit
row and the decimal-string data export.

Most tests here need neither a database nor Redis: psycopg and the session store are
replaced by recording fakes, so the control flow is exercised in any CI job. The ones
that touch real Redis or a real database skip themselves when the resource is absent
or was not opted into.
"""

import json
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.routers as routers
from app.auth.service import (
    AuthService,
    AuthUnavailable,
    InMemoryAuthStore,
    InMemoryRateLimiter,
    InMemorySessionStore,
    PostgresAuthStore,
    RedisSessionStore,
)
from app.contracts import AuthUserResponse
from app.core.config import Settings
from app.demo.lifecycle import _cache_for_reset
from app.demo.operations import DEMO_CACHE_MARKER, DEMO_DB_MARKER
from app.demo.safety import DemoSafetyError
from app.main import app

ORIGIN = {"Origin": "http://localhost:3000"}
EXPECTED_AUDIT_KEYS = {"reason", "result", "request_id", "sessions_revoked"}


def _user(user_id: str | None = None) -> AuthUserResponse:
    return AuthUserResponse(
        id=user_id or str(uuid4()), email=f"{uuid4()}@example.invalid", status="ACTIVE"
    )


def _expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=1)


# --- Recording fakes ---------------------------------------------------------


class _FakeSessions:
    """Session store double that records the marker lifecycle."""

    def __init__(self, fail_revoke: bool = False) -> None:
        self.fail_revoke = fail_revoke
        self.marker: set[str] = set()
        self.calls: list[str] = []

    def available(self) -> bool:
        return True

    def revoke_user(self, user_id: str) -> int:
        self.calls.append("revoke_user")
        self.marker.add(user_id)  # written before anything that can fail, like the real one
        if self.fail_revoke:
            raise AuthUnavailable
        return 2

    def restore_user(self, user_id: str) -> None:
        self.calls.append("restore_user")
        self.marker.discard(user_id)


class _FakeCursor:
    def __init__(self, connection: "_FakeConnection") -> None:
        self.connection = connection

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_exc) -> bool:
        return False

    def execute(self, sql: str, params: tuple | None = None) -> "_FakeCursor":
        self.connection.statements.append((sql, params))
        return self

    def fetchone(self):
        return None

    def fetchall(self):
        return []


class _FakeConnection:
    def __init__(self, fail_commit: bool = False) -> None:
        self.fail_commit = fail_commit
        self.statements: list[tuple[str, tuple | None]] = []
        self.committed = False
        self.rolled_back = False

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type, *_exc) -> bool:
        self.rolled_back = exc_type is not None
        return False

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)

    def execute(self, sql: str, params: tuple | None = None) -> _FakeCursor:
        self.statements.append((sql, params))
        return _FakeCursor(self)

    def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("simulated database outage with a leaked value")
        self.committed = True


def _install(monkeypatch, sessions, connections: list[_FakeConnection]):
    """Route the endpoint to the fakes and return a client authenticated as a fresh user."""
    queue = list(connections)
    opened: list[_FakeConnection] = []

    def connect(*_args, **_kwargs) -> _FakeConnection:
        connection = queue.pop(0) if queue else _FakeConnection()
        opened.append(connection)
        return connection

    auth = AuthService(store=InMemoryAuthStore(), sessions=sessions, limiter=InMemoryRateLimiter())
    monkeypatch.setattr(routers, "psycopg", SimpleNamespace(connect=connect))
    monkeypatch.setattr(routers, "get_auth_service", lambda: auth)
    user = _user()
    app.dependency_overrides[routers.get_current_user] = lambda: user
    return TestClient(app), user, opened


def _audit_rows(connection: _FakeConnection) -> list[tuple]:
    return [
        params for sql, params in connection.statements if sql.startswith("INSERT INTO audit_logs")
    ]


# --- Control flow (no infrastructure) ----------------------------------------


def test_successful_anonymization_writes_audit_in_the_same_transaction(monkeypatch) -> None:
    sessions = _FakeSessions()
    client, user, opened = _install(monkeypatch, sessions, [_FakeConnection()])
    try:
        response = client.delete("/api/v1/account", headers=ORIGIN)
    finally:
        app.dependency_overrides.pop(routers.get_current_user, None)

    assert response.status_code == 204
    main = opened[0]
    assert main.committed and not main.rolled_back
    assert sessions.calls == ["revoke_user"]
    assert user.id in sessions.marker, "the marker must survive a committed anonymization"

    statements = [sql for sql, _ in main.statements]
    order = [
        next(i for i, sql in enumerate(statements) if sql.startswith(prefix))
        for prefix in (
            "UPDATE users",
            "DELETE FROM watchlist_items",
            "DELETE FROM watchlists",
            "UPDATE portfolios",
            "UPDATE portfolio_events",
            "INSERT INTO audit_logs",
        )
    ]
    assert order == sorted(order), "audit row must be the last write before the commit"
    assert not any("sessions" in sql for sql in statements), "sessions live only in Redis"
    assert not any(sql.startswith("DELETE FROM portfolio_events") for sql in statements)
    ledger_writes = [
        (sql, params)
        for sql, params in main.statements
        if sql.startswith("UPDATE portfolio_events")
    ]
    assert ledger_writes == [
        (
            "UPDATE portfolio_events SET note = NULL WHERE note IS NOT NULL "
            "AND portfolio_id IN (SELECT id FROM portfolios WHERE user_id = %s)",
            (user.id,),
        )
    ], "the only ledger write is erasing the user's notes (ADR-010)"

    update_users = next(p for sql, p in main.statements if sql.startswith("UPDATE users"))
    assert update_users[0] == f"deleted-{user.id}@market-pulse.invalid"
    assert user.email not in update_users[0]
    assert update_users[1].startswith("deleted_placeholder_")

    portfolios_sql = next(sql for sql, _ in main.statements if sql.startswith("UPDATE portfolios"))
    assert "archived_at = now()" in portfolios_sql
    assert "'Carteira removida ' || id::text" in portfolios_sql

    (params,) = _audit_rows(main)
    assert params[1] == "USER_ACCOUNT_ANONYMIZED"
    assert params[0] == params[2] == user.id, "target and actor are the anonymized user"
    metadata = json.loads(params[3])
    assert set(metadata) == EXPECTED_AUDIT_KEYS
    assert metadata["reason"] == "LGPD_USER_REQUEST"
    assert metadata["result"] == "success" and metadata["sessions_revoked"] == 2
    assert "@" not in params[3] and user.email not in params[3]


def test_failed_commit_removes_the_revocation_marker(monkeypatch) -> None:
    # The marker blocks every session of the user for the whole session TTL. If the
    # anonymization did not happen, keeping it would lock out a user whose account is intact.
    sessions = _FakeSessions()
    failing, audit = _FakeConnection(fail_commit=True), _FakeConnection()
    client, user, opened = _install(monkeypatch, sessions, [failing, audit])
    try:
        response = client.delete("/api/v1/account", headers=ORIGIN)
    finally:
        app.dependency_overrides.pop(routers.get_current_user, None)

    assert response.status_code == 500
    assert sessions.calls == ["revoke_user", "restore_user"]
    assert user.id not in sessions.marker
    assert failing.rolled_back and not failing.committed

    (params,) = _audit_rows(audit)
    metadata = json.loads(params[3])
    assert params[1] == "USER_ACCOUNT_ANONYMIZED" and params[4] == "failed"
    assert metadata["reason"] == "LGPD_USER_REQUEST"
    assert metadata["error_type"] == "RuntimeError"
    assert "leaked value" not in params[3], "raw exception text must never reach the audit row"
    assert "@" not in params[3]


def test_redis_failure_after_the_marker_rolls_everything_back(monkeypatch) -> None:
    sessions = _FakeSessions(fail_revoke=True)
    main, audit = _FakeConnection(), _FakeConnection()
    client, user, _opened = _install(monkeypatch, sessions, [main, audit])
    try:
        response = client.delete("/api/v1/account", headers=ORIGIN)
    finally:
        app.dependency_overrides.pop(routers.get_current_user, None)

    assert response.status_code == 500
    assert not main.committed and main.rolled_back, "no anonymization without revocation"
    assert sessions.calls == ["revoke_user", "restore_user"]
    assert user.id not in sessions.marker
    assert json.loads(_audit_rows(audit)[0][3])["error_type"] == "AuthUnavailable"


def test_in_memory_revoke_user_only_removes_that_users_sessions() -> None:
    store = InMemorySessionStore()
    target, other = _user(), _user()
    for name, owner in (("a1", target), ("a2", target), ("b1", other)):
        store.create(name, owner, _expiry(), 3600)

    assert store.revoke_user(target.id) == 2
    assert store.get("a1") is None and store.get("a2") is None
    assert store.get("b1") is not None


# --- Real Redis --------------------------------------------------------------


def test_redis_revocation_reaches_every_device_and_blocks_concurrent_sessions(
    _rate_limit_redis_available,
) -> None:
    if not _rate_limit_redis_available:
        pytest.skip("requires a reachable Redis")
    settings = Settings(redis_url=os.environ["MARKET_PULSE_REDIS_URL"], cache_timeout_seconds=5.0)
    store = RedisSessionStore(settings)
    target, other = _user(), _user()
    hashes = {f"{uuid4().hex}": target for _ in range(2)} | {uuid4().hex: other}
    late = uuid4().hex
    try:
        for token_hash, owner in hashes.items():
            store.create(token_hash, owner, _expiry(), 600)
        mine = [h for h, owner in hashes.items() if owner is target]
        theirs = next(h for h, owner in hashes.items() if owner is other)

        assert store.revoke_user(target.id) == 2
        assert all(store.get(h) is None for h in mine)
        assert store.get(theirs) is not None, "other users must keep their sessions"

        # A session created after the marker exists is rejected too (concurrent login).
        store.create(late, target, _expiry(), 600)
        assert store.get(late) is None

        # Undo of the marker: the user is no longer locked out.
        store.restore_user(target.id)
        store.create(late, target, _expiry(), 600)
        assert store.get(late) is not None
    finally:
        for token_hash in [*hashes, late]:
            store.client.delete(f"auth:session:{token_hash}")
        store.client.delete(f"auth:revoked_user:{target.id}")
        store.client.close()


# --- DEMO cache allowlist ----------------------------------------------------


class _FakeCache:
    def __init__(self, keys: list[str]) -> None:
        self.keys = keys

    def get(self, key: str):
        return DEMO_DB_MARKER if key == DEMO_CACHE_MARKER else None

    def scan_iter(self):
        return iter([DEMO_CACHE_MARKER, *self.keys])

    def close(self) -> None:
        return None


def test_demo_reset_accepts_the_revocation_marker_and_still_rejects_unknown_keys(
    monkeypatch,
) -> None:
    from app.demo import lifecycle

    def reset_with(keys: list[str]):
        monkeypatch.setattr(
            lifecycle,
            "Redis",
            SimpleNamespace(from_url=lambda *_a, **_k: _FakeCache(keys)),
            raising=True,
        )
        return _cache_for_reset(SimpleNamespace(redis_url="redis://127.0.0.1:6379/15"))

    _cache, keys = reset_with(["auth:session:abc", f"auth:revoked_user:{uuid4()}"])
    assert len(keys) == 2

    with pytest.raises(DemoSafetyError):
        reset_with(["auth:revoked_user:ok", "something:else"])


# --- Data export -------------------------------------------------------------


class _ExportConnection:
    """Answers the four export queries with fixed rows, selected by table."""

    ledger_row = (
        uuid4(),
        uuid4(),
        "BUY",
        date(2026, 9, 1),
        uuid4(),
        "equity.br.b3.petr4",
        Decimal("10.50000000"),
        Decimal("50.12345678"),
        Decimal("526.29000000"),
        Decimal("1.00000000"),
        None,
        "BRL",
        datetime(2026, 9, 1, tzinfo=timezone.utc),
        "nota escrita pelo proprio usuario",
    )

    def __init__(self, user_id: str, email: str) -> None:
        self.user_id, self.email = user_id, email

    def __enter__(self) -> "_ExportConnection":
        return self

    def __exit__(self, *_exc) -> bool:
        return False

    def commit(self) -> None:
        return None

    def execute(self, sql: str, params: tuple | None = None):
        created = datetime(2026, 8, 1, tzinfo=timezone.utc)
        if "FROM users" in sql:
            rows = [(self.user_id, self.email, "ACTIVE", created)]
        elif "FROM watchlists" in sql:
            rows = []
        elif "FROM portfolios" in sql:
            rows = [(uuid4(), "Carteira", "BRL", created, None)]
        elif "FROM portfolio_events" in sql:
            rows = [self.ledger_row]
        else:
            rows = []
        return SimpleNamespace(fetchone=lambda: rows[0] if rows else None, fetchall=lambda: rows)


def _no_floats(value) -> None:
    assert not isinstance(value, float), f"float leaked into the export: {value!r}"
    if isinstance(value, dict):
        for item in value.values():
            _no_floats(item)
    elif isinstance(value, list):
        for item in value:
            _no_floats(item)


def test_data_export_uses_decimal_strings_and_includes_the_users_notes(monkeypatch) -> None:
    user = _user()
    monkeypatch.setattr(
        routers,
        "psycopg",
        SimpleNamespace(connect=lambda *_a, **_k: _ExportConnection(user.id, user.email)),
    )
    app.dependency_overrides[routers.get_current_user] = lambda: user
    try:
        response = TestClient(app).get("/api/v1/account/data-export", headers=ORIGIN)
    finally:
        app.dependency_overrides.pop(routers.get_current_user, None)

    assert response.status_code == 200
    body = response.json()
    _no_floats(body)
    event = body["ledger"][0]
    # Trailing zeros prove these are not float round-trips (a float would print 10.5).
    assert event["quantity"] == "10.50000000"
    assert event["price"] == "50.12345678"
    assert event["gross_amount"] == "526.29000000"
    assert event["fees"] == "1.00000000"
    assert event["cash_amount"] is None
    assert event["note"] == "nota escrita pelo proprio usuario"


# --- Real database (opt-in, disposable database only) ------------------------


@pytest.mark.skipif(
    os.environ.get("MARKET_PULSE_ACCOUNT_LIFECYCLE") != "true",
    reason="writes ledger rows the append-only trigger forbids deleting, so it requires "
    "an explicitly dedicated disposable local database",
)
def test_anonymization_end_to_end_on_a_real_database(monkeypatch) -> None:
    import psycopg

    url = os.environ.get("MARKET_PULSE_ACCOUNT_LIFECYCLE_DATABASE_URL", "")
    if "127.0.0.1" not in url or "market_pulse_demo" in url:
        raise AssertionError(
            "MARKET_PULSE_ACCOUNT_LIFECYCLE_DATABASE_URL must target a local disposable "
            "database that is not the seeded DEMO database"
        )
    settings = Settings(
        database_url=url,
        redis_url=os.environ["MARKET_PULSE_REDIS_URL"],
        cache_timeout_seconds=5.0,
    )
    sessions = RedisSessionStore(settings)
    auth = AuthService(
        store=PostgresAuthStore(settings),
        sessions=sessions,
        limiter=InMemoryRateLimiter(),
        settings=settings,
    )
    monkeypatch.setattr(routers, "get_settings", lambda: settings)
    monkeypatch.setattr(routers, "get_auth_service", lambda: auth)

    email = f"anon-{uuid4()}@example.invalid"
    original_note = "nota com possivel dado pessoal"
    with psycopg.connect(url) as conn:
        user_id = str(
            conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
                (email, "argon2-placeholder-not-a-real-hash"),
            ).fetchone()[0]
        )
        portfolio_id = str(
            conn.execute(
                "INSERT INTO portfolios (user_id, name, base_currency) VALUES (%s, %s, 'BRL') "
                "RETURNING id",
                (user_id, "Carteira da Maria Silva"),
            ).fetchone()[0]
        )
        event_id = str(
            conn.execute(
                "INSERT INTO portfolio_events (portfolio_id, event_type, event_date, currency, "
                "cash_amount, created_by, idempotency_key, request_id, note) "
                "VALUES (%s, 'CASH_DEPOSIT', %s, 'BRL', '100.00', %s, %s, 'anon', %s) "
                "RETURNING id",
                (portfolio_id, "2026-09-01", user_id, f"anon-{uuid4()}", original_note),
            ).fetchone()[0]
        )
        conn.execute("INSERT INTO watchlists (user_id, name) VALUES (%s, 'Acompanhar')", (user_id,))
        conn.commit()

        user = AuthUserResponse(id=user_id, email=email, status="ACTIVE")
        tokens = [uuid4().hex, uuid4().hex]
        hashes = [auth._hash_token(token) for token in tokens]
        try:
            for token_hash in hashes:
                sessions.create(token_hash, user, _expiry(), 600)

            client = TestClient(app)
            client.cookies.set("market_pulse_session", tokens[0])
            assert client.get("/api/v1/auth/me").status_code == 200

            response = client.delete("/api/v1/account", headers=ORIGIN)
            assert response.status_code == 204

            # The other device (never used in this request) is logged out as well.
            other = TestClient(app)
            other.cookies.set("market_pulse_session", tokens[1])
            assert other.get("/api/v1/auth/me").status_code == 401

            # The old credentials no longer open a session.
            login = TestClient(app).post(
                "/api/v1/auth/login",
                json={"email": email, "password": "Str0ng-password-123"},
                headers=ORIGIN,
            )
            assert login.status_code == 401

            account = conn.execute(
                "SELECT email, status FROM users WHERE id = %s", (user_id,)
            ).fetchone()
            assert account == (f"deleted-{user_id}@market-pulse.invalid", "DELETED")

            portfolio = conn.execute(
                "SELECT name, base_currency, archived_at, user_id FROM portfolios WHERE id = %s",
                (portfolio_id,),
            ).fetchone()
            assert portfolio[0] == f"Carteira removida {portfolio_id}"
            assert "Maria" not in portfolio[0]
            assert portfolio[1] == "BRL" and portfolio[2] is not None
            assert str(portfolio[3]) == user_id

            ledger_columns = (
                "SELECT note, portfolio_id, event_type, event_date, currency, cash_amount, "
                "created_by, idempotency_key, request_id FROM portfolio_events WHERE id = %s"
            )
            ledger = conn.execute(ledger_columns, (event_id,)).fetchone()
            # ADR-010 (H-08): the free-text note is erased; the financial record is intact.
            assert ledger[0] is None
            assert (str(ledger[1]), ledger[2], str(ledger[3]), ledger[4]) == (
                portfolio_id,
                "CASH_DEPOSIT",
                "2026-09-01",
                "BRL",
            )
            assert ledger[5] == Decimal("100.00") and str(ledger[6]) == user_id
            assert ledger[7].startswith("anon-") and ledger[8] == "anon"

            # The trigger still refuses every other change, including re-filling the note.
            for forbidden in (
                "UPDATE portfolio_events SET cash_amount = '1.00' WHERE id = %s",
                "UPDATE portfolio_events SET note = 'reescrita' WHERE id = %s",
                "UPDATE portfolio_events SET note = NULL, currency = 'USD' WHERE id = %s",
                "DELETE FROM portfolio_events WHERE id = %s",
            ):
                with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
                    with conn.transaction():
                        conn.execute(forbidden, (event_id,))
            assert conn.execute(ledger_columns, (event_id,)).fetchone() == ledger

            rows = conn.execute(
                "SELECT entity_type, entity_id, actor_user_id, resource, result, request_id, "
                "metadata FROM audit_logs WHERE entity_id = %s AND action = %s",
                (user_id, "USER_ACCOUNT_ANONYMIZED"),
            ).fetchall()
            assert len(rows) == 1
            entity_type, entity_id, actor, resource, result, request_id, metadata = rows[0]
            assert (entity_type, str(entity_id), str(actor)) == ("user", user_id, user_id)
            assert (resource, result) == ("account", "success")
            assert request_id == response.headers["x-request-id"]
            assert set(metadata) == EXPECTED_AUDIT_KEYS
            assert metadata["reason"] == "LGPD_USER_REQUEST"
            flattened = json.dumps(metadata)
            assert email not in flattened and "@" not in flattened and "Maria" not in flattened
        finally:
            for token_hash in hashes:
                sessions.client.delete(f"auth:session:{token_hash}")
            sessions.client.delete(f"auth:revoked_user:{user_id}")
            sessions.client.close()
