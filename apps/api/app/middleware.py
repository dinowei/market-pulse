"""HTTP middleware for Market Pulse API.

Classes
-------
RequestIdMiddleware
    Generates or propagates an X-Request-ID for every request.
SecurityHeadersMiddleware
    Adds standard defensive security response headers.
CSRFMiddleware
    Validates Origin/Referer for state-changing authenticated requests.
RateLimitMiddleware
    Enforces per-IP rate limits with clear resolution order and fail-open/
    fail-closed semantics per endpoint category.
"""

from uuid import UUID, uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import get_settings

TELEMETRY_PATH = "/api/v1/telemetry/web-vitals"
TELEMETRY_RATE_LIMIT_MAX = 30


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Request-ID")
        try:
            value = str(UUID(incoming)) if incoming else str(uuid4())
        except ValueError:
            value = str(uuid4())
        request.state.request_id = value
        response = await call_next(request)
        response.headers["X-Request-ID"] = value
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


SECRET_AUTHENTICATED_PATHS = frozenset({"/api/v1/internal/refresh-quotes"})
"""Routes authenticated by their own shared secret, never by a browser session.

/api/v1/internal/refresh-quotes is called by the scheduled job with X-Cron-Secret
compared via secrets.compare_digest. Such callers have no browser Origin, and a
forged cross-site request cannot supply the secret, so the Origin allowlist adds
nothing and would only break the job. Only add a path here when it is authenticated
by a secret the browser never holds — never for cookie-authenticated routes.
"""


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validates Origin/Referer against the allowlist on every state-changing request.

    The check no longer depends on a session cookie being present: an unauthenticated
    mutating request from a disallowed origin (login/register being the notable case)
    is rejected too, so DEMO and production behave identically.

    A request carrying neither Origin nor Referer is only rejected when it also
    carries a session cookie. Browsers always send Origin on cross-site mutating
    requests, so a header-less request is a non-browser client with no ambient
    credentials to abuse - that is not a CSRF vector, and rejecting it would break
    legitimate server-to-server and CLI callers.
    """

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()

        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and request.url.path not in SECRET_AUTHENTICATED_PATHS
        ):
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")

            if origin:
                allowed = origin in settings.cors_origins
            elif referer:
                allowed = any(referer.startswith(o) for o in settings.cors_origins)
            else:
                allowed = not request.cookies.get(settings.auth_cookie_name)

            if not allowed:
                from app.errors import problem

                return problem(
                    request,
                    403,
                    "Forbidden",
                    "CSRF protection: Origin or Referer is not in the allowlist.",
                    "FORBIDDEN",
                )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforces per-IP rate limits.

    Limiter resolution order (first non-None wins):
      1. request.app.state.rate_limiter - injected by startup hooks or test fixtures
      2. get_auth_service().limiter - production Redis-backed limiter
      3. InMemoryRateLimiter() - used if step 2 raises and fail_closed is False

    Exactly ONE call to limiter.allow() is made per request.
    """

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        path = request.url.path

        if "/api/v1/auth/login" in path or "/api/v1/auth/register" in path:
            window = settings.auth_rate_limit_window_seconds
            limit = settings.auth_rate_limit_max_attempts
            key_prefix = "rate_limit:auth"
            fail_closed = True
        elif (
            path.startswith("/health")
            or "/api/v1/instruments" in path
            or "/api/v1/market-data" in path
            or "/api/v1/history" in path
        ):
            window = 60
            limit = 100
            key_prefix = "rate_limit:public"
            fail_closed = False
        elif path == TELEMETRY_PATH:
            # Anonymous beacons must not drain the bucket that protects the authenticated
            # routes (found by the E2E on 2026-10-01): own bucket, same 30/60 s.
            window = 60
            limit = TELEMETRY_RATE_LIMIT_MAX
            key_prefix = "rate_limit:telemetry"
            fail_closed = False
        else:
            window = 60
            limit = 30
            key_prefix = "rate_limit:standard"
            fail_closed = False

        ip = request.client.host if request.client else "unknown"
        key = f"{key_prefix}:{ip}"

        limiter = getattr(getattr(request, "app", None), "state", None)
        limiter = getattr(limiter, "rate_limiter", None) if limiter is not None else None

        if limiter is None:
            try:
                from app.routers import get_auth_service

                limiter = get_auth_service().limiter
            except Exception:
                pass

        if limiter is None:
            if fail_closed:
                from app.errors import problem

                return problem(
                    request,
                    503,
                    "Service Unavailable",
                    "Rate limiting service is currently unavailable.",
                    "SERVICE_UNAVAILABLE",
                )
            from app.auth.service import InMemoryRateLimiter

            limiter = InMemoryRateLimiter(max_attempts=limit)

        try:
            effective_max = getattr(limiter, "max_attempts", limit)
            allowed = limiter.allow(key, window_seconds=window, max_attempts=effective_max)
        except Exception:
            if fail_closed:
                from app.errors import problem

                return problem(
                    request,
                    503,
                    "Service Unavailable",
                    "Rate limiting service is currently unavailable.",
                    "SERVICE_UNAVAILABLE",
                )
            return await call_next(request)

        if not allowed:
            from app.errors import problem

            response = problem(
                request,
                429,
                "Too Many Requests",
                "Rate limit exceeded.",
                "RATE_LIMITED",
            )
            response.headers["Retry-After"] = str(window)
            return response

        return await call_next(request)
