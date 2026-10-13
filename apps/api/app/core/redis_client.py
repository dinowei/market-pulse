"""One Redis client, and so one connection pool, per process and configuration (H-24).

`get_auth_service()` builds a new AuthService on every call, and the middleware and the
routes call it more than once per request. Each service used to open its own clients;
sharing them keeps connections pooled instead of reconnecting on every request.
"""

from functools import lru_cache

from redis import Redis


@lru_cache(maxsize=8)
def shared_redis(url: str, timeout_seconds: float) -> Redis:
    return Redis.from_url(
        url,
        socket_connect_timeout=timeout_seconds,
        socket_timeout=timeout_seconds,
        decode_responses=True,
    )
