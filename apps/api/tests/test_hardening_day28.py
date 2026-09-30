import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.routers as routers
from app.auth.service import InMemoryRateLimiter
from app.core.config import (
    ProductionConfigurationError,
    Settings,
    validate_production_settings,
)
from app.main import app


def _refresh_run_summary() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "run_id": str(uuid4()),
        "status": "SUCCESS",
        "started_at": now,
        "finished_at": now,
        "total_items": 1,
        "succeeded_items": 1,
        "failed_items": 0,
        "skipped_items": 0,
        "quarantined_items": 0,
        "cache_invalidated_items": 1,
        "data_level": "DEMO",
        "warnings": [],
        "request_id": str(uuid4()),
    }


def test_security_headers_present() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("Content-Security-Policy") == "default-src 'self'"
    hsts = "max-age=63072000; includeSubDomains; preload"
    assert headers.get("Strict-Transport-Security") == hsts
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_global_rate_limiting_enforced(monkeypatch) -> None:
    # Set up an InMemoryRateLimiter with max_attempts = 2 for testing
    limiter = InMemoryRateLimiter(max_attempts=2)
    # Inject via app.state.rate_limiter without client-controlled headers
    app.state.rate_limiter = limiter
    try:
        client = TestClient(app)
        for _ in range(2):
            resp = client.post("/api/v1/auth/login", json={})
            assert resp.status_code != 429

        # The 3rd request must fail with 429 Too Many Requests
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "60"
        assert resp.json()["code"] == "RATE_LIMITED"
    finally:
        app.state.rate_limiter = None


def test_csrf_rejects_disallowed_origin_without_session_cookie() -> None:
    # Regression: the Day 28 middleware rewrite dropped main.py's demo_origin_guard and
    # only checked Origin when a session cookie was present, so login/register (which
    # never carry one) accepted any origin.
    client = TestClient(app)

    rejected = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.invalid", "password": "Str0ng-password-123"},
        headers={"Origin": "https://untrusted.invalid"},
    )
    assert rejected.status_code == 403
    assert "CSRF" in rejected.json()["detail"]

    allowed = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.invalid", "password": "Str0ng-password-123"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert allowed.status_code != 403


def test_secret_authenticated_cron_route_is_exempt_from_origin_check(monkeypatch) -> None:
    # The scheduled job sends no browser Origin; X-Cron-Secret is its authentication,
    # so the Origin allowlist must not stand in front of it.
    monkeypatch.setattr(
        routers,
        "get_settings",
        lambda: Settings(internal_refresh_secret="local_demo_only_change_me"),
    )
    monkeypatch.setattr(routers, "refresh_market_data", lambda **_: _refresh_run_summary())

    response = TestClient(app).post(
        "/api/v1/internal/refresh-quotes",
        json={
            "dataset": "demo-quotes",
            "capability": "latest_quote",
            "canonical_ids": ["equity.br.b3.petr4"],
            "mode": "DEMO_ONLY",
        },
        headers={"X-Cron-Secret": "local_demo_only_change_me"},
    )
    assert response.status_code == 200


def test_csrf_middleware_protection() -> None:
    client = TestClient(app)
    cookie = {"market_pulse_session": "dummy-token-session"}

    # 1. Mutating request with auth cookie but no Origin or Referer -> 403 Forbidden
    resp = client.post("/api/v1/auth/logout", cookies=cookie)
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]

    # 2. Mutating request with auth cookie and external/unauthorized Origin -> 403 Forbidden
    resp = client.post("/api/v1/auth/logout", cookies=cookie, headers={"Origin": "http://evil-attacker.com"})
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]

    # 3. Mutating request with auth cookie and allowed Origin -> passes CSRF check
    resp = client.post("/api/v1/auth/logout", cookies=cookie, headers={"Origin": "http://localhost:3000"})
    assert resp.status_code != 403
    assert resp.status_code in {204, 401, 503}


def test_strict_production_config_validation() -> None:
    # 1. Local environment allows defaults
    local_cfg = Settings(environment="local")
    validate_production_settings(local_cfg)  # must not raise

    # 2. Production with default/insecure database password must be rejected
    insecure_db_cfg = Settings(
        environment="production",
        database_url="postgresql://market_pulse:market_pulse_local_only@prod.db:5432/market_pulse",
        redis_url="redis://prod.redis:6379/0",
        internal_refresh_secret="production-secret-of-sufficient-length-12345",
        cors_origins=["https://marketpulse.com"],
        demo_enabled=False,
    )
    with pytest.raises(ProductionConfigurationError, match="MARKET_PULSE_DATABASE_URL"):
        validate_production_settings(insecure_db_cfg)

    # 3. Production with DEMO enabled must be rejected
    demo_in_prod = Settings(
        environment="production",
        database_url="postgresql://market_pulse:strong_real_pw_prod@prod.db:5432/market_pulse",
        redis_url="redis://prod.redis:6379/0",
        internal_refresh_secret="production-secret-of-sufficient-length-12345",
        cors_origins=["https://marketpulse.com"],
        demo_enabled=True,
    )
    with pytest.raises(ProductionConfigurationError, match="DEMO_ENABLED"):
        validate_production_settings(demo_in_prod)

    # 4. Production with missing internal refresh secret must be rejected
    no_secret_cfg = Settings(
        environment="production",
        database_url="postgresql://market_pulse:strong_real_pw_prod@prod.db:5432/market_pulse",
        redis_url="redis://prod.redis:6379/0",
        internal_refresh_secret=None,
        cors_origins=["https://marketpulse.com"],
        demo_enabled=False,
    )
    with pytest.raises(ProductionConfigurationError, match="INTERNAL_REFRESH_SECRET"):
        validate_production_settings(no_secret_cfg)

    # 5. Production with wildcard CORS must be rejected
    wildcard_cors_cfg = Settings(
        environment="production",
        database_url="postgresql://market_pulse:strong_real_pw_prod@prod.db:5432/market_pulse",
        redis_url="redis://prod.redis:6379/0",
        internal_refresh_secret="production-secret-of-sufficient-length-12345",
        cors_origins=["*"],
        demo_enabled=False,
    )
    with pytest.raises(ProductionConfigurationError, match="CORS_ORIGINS"):
        validate_production_settings(wildcard_cors_cfg)

    # 6. Production with localhost CORS must be rejected
    localhost_cors_cfg = Settings(
        environment="production",
        database_url="postgresql://market_pulse:strong_real_pw_prod@prod.db:5432/market_pulse",
        redis_url="redis://prod.redis:6379/0",
        internal_refresh_secret="production-secret-of-sufficient-length-12345",
        cors_origins=["http://localhost:3000"],
        demo_enabled=False,
    )
    with pytest.raises(ProductionConfigurationError, match="cannot reference local host"):
        validate_production_settings(localhost_cors_cfg)

    # 7. Valid production configuration passes
    valid_prod_cfg = Settings(
        environment="production",
        database_url="postgresql://market_pulse:strong_real_pw_prod@prod.db:5432/market_pulse",
        redis_url="redis://prod.redis:6379/0",
        internal_refresh_secret="production-secret-of-sufficient-length-12345",
        cors_origins=["https://marketpulse.com", "https://app.marketpulse.com"],
        demo_enabled=False,
    )
    validate_production_settings(valid_prod_cfg)  # must not raise


def test_account_endpoints_registered() -> None:
    all_paths = {r.path for r in app.routes if hasattr(r, "path")} | {
        f"/api/v1{r.path}" for r in routers.router.routes if hasattr(r, "path")
    } | {r.path for r in routers.router.routes if hasattr(r, "path")}
    assert any("/account/data-export" in p for p in all_paths)
    assert any(p.endswith("/account") for p in all_paths)


def _account_fixture(conn, email: str) -> tuple[str, str, str]:
    """Persist a user with one portfolio, one ledger event and one watchlist."""
    user_id = str(
        conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
            (email, "argon2-placeholder-not-a-real-hash"),
        ).fetchone()[0]
    )
    portfolio_id = str(
        conn.execute(
            "INSERT INTO portfolios (user_id, name, base_currency) "
            "VALUES (%s, %s, %s) RETURNING id",
            (user_id, "Carteira hardening", "BRL"),
        ).fetchone()[0]
    )
    event_id = str(
        conn.execute(
            "INSERT INTO portfolio_events (portfolio_id, event_type, event_date, currency, "
            "cash_amount, created_by, idempotency_key, request_id) "
            "VALUES (%s, 'CASH_DEPOSIT', %s, 'BRL', %s, %s, %s, %s) RETURNING id",
            (portfolio_id, "2026-09-01", "100.00", user_id, f"hardening-{uuid4()}", "hardening"),
        ).fetchone()[0]
    )
    conn.execute("INSERT INTO watchlists (user_id, name) VALUES (%s, %s)", (user_id, "Acompanhar"))
    conn.commit()
    return user_id, portfolio_id, event_id


@pytest.mark.skipif(
    os.environ.get("MARKET_PULSE_ACCOUNT_LIFECYCLE") != "true",
    reason="writes a ledger row that the append-only trigger forbids deleting, so it "
    "requires an explicitly dedicated disposable local database",
)
def test_account_deletion_anonymizes_and_preserves_append_only_ledger(monkeypatch) -> None:
    # Documented decision: DELETE /api/v1/account anonymizes instead of hard-deleting,
    # because portfolio_events and audit_logs are append-only financial/audit records
    # (a database trigger, prevent_immutable_portfolio_event_change, enforces it).
    import psycopg

    url = os.environ.get("MARKET_PULSE_ACCOUNT_LIFECYCLE_DATABASE_URL", "")
    if "127.0.0.1" not in url or "market_pulse_demo" in url:
        raise AssertionError(
            "MARKET_PULSE_ACCOUNT_LIFECYCLE_DATABASE_URL must target a local disposable "
            "database that is not the seeded DEMO database"
        )
    monkeypatch.setattr(routers, "get_settings", lambda: Settings(database_url=url))

    email = f"hardening-{uuid4()}@example.invalid"
    with psycopg.connect(url) as conn:
        user_id, portfolio_id, event_id = _account_fixture(conn, email)
        user = routers.AuthUserResponse(id=user_id, email=email, status="ACTIVE")
        app.dependency_overrides[routers.get_current_user] = lambda: user
        try:
            client = TestClient(app)
            origin = {"Origin": "http://localhost:3000"}

            export = client.get("/api/v1/account/data-export", headers=origin)
            assert export.status_code == 200
            assert email in export.text
            assert portfolio_id in export.text

            deleted = client.delete("/api/v1/account", headers=origin)
            assert deleted.status_code == 204
        finally:
            app.dependency_overrides.pop(routers.get_current_user, None)

        row = conn.execute(
            "SELECT email, password_hash, status FROM users WHERE id = %s", (user_id,)
        ).fetchone()
        assert row is not None, "the user row must survive as an anonymized record"
        assert row[0] == f"deleted-{user_id}@market-pulse.invalid"
        assert email not in row[0]
        assert row[1] != "argon2-placeholder-not-a-real-hash"
        assert row[2] == "DELETED"

        assert conn.execute(
            "SELECT archived_at FROM portfolios WHERE id = %s", (portfolio_id,)
        ).fetchone()[0] is not None
        assert conn.execute(
            "SELECT COUNT(*) FROM watchlists WHERE user_id = %s", (user_id,)
        ).fetchone()[0] == 0
        # The ledger is the point: it must still be there, untouched.
        assert conn.execute(
            "SELECT COUNT(*) FROM portfolio_events WHERE id = %s", (event_id,)
        ).fetchone()[0] == 1


def test_backup_restore_manifest_roundtrip() -> None:
    import sys
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from scripts.backup import create_backup_manifest
    from scripts.restore import verify_manifest

    with TemporaryDirectory() as tmpdir:
        backup_dir = Path(tmpdir)
        pg_meta = {"file": "market_pulse_postgres.dump", "size_bytes": 1024, "sha256": "abc123"}
        redis_meta = {"redis_target": "redis://127.0.0.1:6379/0", "status": "bgsave_triggered"}

        manifest_path = create_backup_manifest(backup_dir, pg_meta, redis_meta, "production")
        assert manifest_path.exists()

        verified = verify_manifest(manifest_path)
        assert verified["environment"] == "production"
        assert verified["postgres_backup"]["file"] == "market_pulse_postgres.dump"
        assert verified["postgres_backup"]["sha256"] == "abc123"


def test_production_mode_smoke() -> None:
    client = TestClient(app)

    # /health/live
    live_resp = client.get("/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["status"] == "ok"

    # /health
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    # /api/v1/instruments (public catalog)
    inst_resp = client.get("/api/v1/instruments")
    assert inst_resp.status_code == 200
    assert "items" in inst_resp.json()


def test_env_example_synchronization() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    env_example_path = repo_root / ".env.example"
    assert env_example_path.exists(), ".env.example must exist in repo root"

    with open(env_example_path, encoding="utf-8") as f:
        lines = f.readlines()

    example_keys = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            example_keys.add(key)

    for field_name in Settings.model_fields.keys():
        expected_var = f"MARKET_PULSE_{field_name.upper()}"
        assert expected_var in example_keys, (
            f"Field '{field_name}' ({expected_var}) missing from .env.example"
        )
