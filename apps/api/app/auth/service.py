from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4

import psycopg
from redis import Redis

from app.auth.passwords import hash_password, verify_dummy, verify_password
from app.contracts import AuthUserResponse, LoginRequest, RegisterRequest
from app.core.config import Settings, get_settings


class AuthUnavailable(RuntimeError):
    """The session or rate-limit dependency is unavailable."""


class AuthConflict(RuntimeError):
    """Registration conflicts without revealing account details."""


class AuthInvalid(RuntimeError):
    """Credentials or session are invalid."""


class AuthRateLimited(RuntimeError):
    """Authentication attempts exceeded the configured limit."""


class AuthStore(Protocol):
    def create_user(self, email: str, password_hash: str) -> AuthUserResponse: ...

    def find_user(self, email: str) -> tuple[AuthUserResponse, str] | None: ...


class SessionStore(Protocol):
    def create(
        self, token_hash: str, user: AuthUserResponse, expires_at: datetime, ttl: int
    ) -> None: ...

    def get(self, token_hash: str) -> AuthUserResponse | None: ...

    def revoke(self, token_hash: str) -> None: ...

    def revoke_user(self, user_id: str) -> int: ...

    def restore_user(self, user_id: str) -> None: ...

    def available(self) -> bool: ...


class PostgresAuthStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def create_user(self, email: str, password_hash: str) -> AuthUserResponse:
        try:
            with psycopg.connect(self.settings.database_url) as connection:
                row = connection.execute(
                    "INSERT INTO users (email, password_hash) VALUES (%s, %s) "
                    "RETURNING id, email, status",
                    (email, password_hash),
                ).fetchone()
                connection.commit()
        except psycopg.errors.UniqueViolation as exc:
            raise AuthConflict from exc
        if row is None:
            raise AuthUnavailable
        return AuthUserResponse(id=str(row[0]), email=str(row[1]), status=str(row[2]))

    def find_user(self, email: str) -> tuple[AuthUserResponse, str] | None:
        with psycopg.connect(self.settings.database_url) as connection:
            row = connection.execute(
                "SELECT id, email, status, password_hash FROM users "
                "WHERE email=%s AND status='ACTIVE'",
                (email,),
            ).fetchone()
        if row is None:
            return None
        return AuthUserResponse(id=str(row[0]), email=str(row[1]), status=str(row[2])), str(row[3])


class RedisSessionStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=settings.cache_timeout_seconds,
            socket_timeout=settings.cache_timeout_seconds,
            decode_responses=True,
        )

    def available(self) -> bool:
        try:
            return bool(self.client.ping())
        except Exception:
            return False

    def create(
        self, token_hash: str, user: AuthUserResponse, expires_at: datetime, ttl: int
    ) -> None:
        try:
            self.client.hset(
                f"auth:session:{token_hash}",
                mapping={
                    "user_id": user.id,
                    "email": user.email,
                    "status": user.status,
                    "expires_at": expires_at.isoformat(),
                },
            )
            self.client.expire(f"auth:session:{token_hash}", ttl)
        except Exception as exc:
            raise AuthUnavailable from exc

    def get(self, token_hash: str) -> AuthUserResponse | None:
        try:
            values = self.client.hgetall(f"auth:session:{token_hash}")
        except Exception as exc:
            raise AuthUnavailable from exc
        if not values:
            return None
        try:
            if datetime.fromisoformat(values["expires_at"]) <= datetime.now(timezone.utc):
                self.revoke(token_hash)
                return None
            if self._user_revoked(values["user_id"]):
                self.revoke(token_hash)
                return None
            return AuthUserResponse(
                id=values["user_id"], email=values["email"], status=values["status"]
            )
        except (KeyError, ValueError) as exc:
            raise AuthUnavailable from exc

    def revoke(self, token_hash: str) -> None:
        try:
            self.client.delete(f"auth:session:{token_hash}")
        except Exception as exc:
            raise AuthUnavailable from exc

    @staticmethod
    def _revoked_key(user_id: str) -> str:
        return f"auth:revoked_user:{user_id}"

    def _user_revoked(self, user_id: str) -> bool:
        try:
            return bool(self.client.exists(self._revoked_key(user_id)))
        except Exception as exc:
            raise AuthUnavailable from exc

    def revoke_user(self, user_id: str) -> int:
        # Sessions are keyed by token hash with no per-user index, so a scan is the only
        # way to reach the other devices. The marker is written first so that a session
        # created or read while the scan runs is rejected as well.
        try:
            self.client.set(
                self._revoked_key(user_id), "1", ex=self.settings.auth_session_ttl_seconds
            )
            removed = 0
            for key in self.client.scan_iter(match="auth:session:*", count=500):
                if self.client.hget(key, "user_id") == user_id:
                    removed += int(self.client.delete(key))
            return removed
        except Exception as exc:
            raise AuthUnavailable from exc

    def restore_user(self, user_id: str) -> None:
        # Undo of the marker only. Sessions already deleted by revoke_user stay deleted:
        # the user logs in again, which beats being locked out for the whole session TTL.
        try:
            self.client.delete(self._revoked_key(user_id))
        except Exception as exc:
            raise AuthUnavailable from exc


class RedisRateLimiter:
    def __init__(self, settings: Settings):
        self.client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=settings.cache_timeout_seconds,
            socket_timeout=settings.cache_timeout_seconds,
            decode_responses=True,
        )
        self.settings = settings

    def allow(
        self,
        key: str,
        window_seconds: int | None = None,
        max_attempts: int | None = None,
    ) -> bool:
        try:
            w = (
                window_seconds
                if window_seconds is not None
                else self.settings.auth_rate_limit_window_seconds
            )
            m = (
                max_attempts
                if max_attempts is not None
                else self.settings.auth_rate_limit_max_attempts
            )
            current = int(self.client.incr(key))
            if current == 1:
                self.client.expire(key, w)
            return current <= m
        except Exception as exc:
            raise AuthUnavailable from exc


class InMemoryAuthStore:
    def __init__(self):
        self.users: dict[str, tuple[AuthUserResponse, str]] = {}

    def create_user(self, email: str, password_hash: str) -> AuthUserResponse:
        if email in self.users:
            raise AuthConflict
        user = AuthUserResponse(id=str(uuid4()), email=email, status="ACTIVE")
        self.users[email] = (user, password_hash)
        return user

    def find_user(self, email: str) -> tuple[AuthUserResponse, str] | None:
        return self.users.get(email)


class InMemorySessionStore:
    def __init__(self):
        self.sessions: dict[str, tuple[AuthUserResponse, datetime]] = {}

    def available(self) -> bool:
        return True

    def create(
        self, token_hash: str, user: AuthUserResponse, expires_at: datetime, ttl: int
    ) -> None:
        self.sessions[token_hash] = (user, expires_at)

    def get(self, token_hash: str) -> AuthUserResponse | None:
        value = self.sessions.get(token_hash)
        if value is None:
            return None
        if value[1] <= datetime.now(timezone.utc):
            self.sessions.pop(token_hash, None)
            return None
        return value[0]

    def revoke(self, token_hash: str) -> None:
        self.sessions.pop(token_hash, None)

    def revoke_user(self, user_id: str) -> int:
        doomed = [h for h, (user, _) in self.sessions.items() if user.id == user_id]
        for token_hash in doomed:
            self.sessions.pop(token_hash, None)
        return len(doomed)

    def restore_user(self, user_id: str) -> None:
        # No marker exists in memory; deleted sessions are not brought back.
        return None


class InMemoryRateLimiter:
    def __init__(self, max_attempts: int = 5):
        self.max_attempts = max_attempts
        self.counts: dict[str, int] = {}

    def allow(
        self,
        key: str,
        window_seconds: int | None = None,
        max_attempts: int | None = None,
    ) -> bool:
        self.counts[key] = self.counts.get(key, 0) + 1
        m = max_attempts if max_attempts is not None else self.max_attempts
        return self.counts[key] <= m


@dataclass
class AuthService:
    store: AuthStore | None = None
    sessions: SessionStore | None = None
    limiter: RedisRateLimiter | InMemoryRateLimiter | None = None
    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()
        self.store = self.store or PostgresAuthStore(self.settings)
        self.sessions = self.sessions or RedisSessionStore(self.settings)
        self.limiter = self.limiter or RedisRateLimiter(self.settings)

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _rate_limit(self, key: str) -> None:
        if self.limiter is None:
            raise AuthUnavailable
        if not self.limiter.allow(key):
            raise AuthRateLimited

    def register(self, payload: RegisterRequest, ip: str) -> AuthUserResponse:
        self._rate_limit(f"auth:register:ip:{ip}")
        assert self.store is not None
        return self.store.create_user(payload.email, hash_password(payload.password))

    def login(self, payload: LoginRequest, ip: str) -> tuple[AuthUserResponse, str, datetime]:
        self._rate_limit(f"auth:login:ip:{ip}")
        assert self.store is not None
        found = self.store.find_user(payload.email)
        if found is None:
            verify_dummy(payload.password)
            raise AuthInvalid
        user, password_hash = found
        if not verify_password(payload.password, password_hash):
            raise AuthInvalid
        if self.sessions is None or not self.sessions.available():
            raise AuthUnavailable
        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self.settings.auth_session_ttl_seconds
        )  # type: ignore[union-attr]
        self.sessions.create(
            self._hash_token(token), user, expires_at, self.settings.auth_session_ttl_seconds
        )  # type: ignore[union-attr]
        return user, token, expires_at

    def me(self, token: str | None) -> AuthUserResponse:
        if not token or self.sessions is None:
            raise AuthInvalid
        user = self.sessions.get(self._hash_token(token))
        if user is None:
            raise AuthInvalid
        return user

    def logout(self, token: str | None) -> None:
        if token and self.sessions is not None:
            self.sessions.revoke(self._hash_token(token))

    def revoke_user(self, user_id: str) -> int:
        if self.sessions is None:
            raise AuthUnavailable
        return self.sessions.revoke_user(user_id)

    def restore_user(self, user_id: str) -> None:
        if self.sessions is None:
            raise AuthUnavailable
        self.sessions.restore_user(user_id)
