from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import asyncpg
from redis.asyncio import Redis

from app.core.config import Settings


def _asyncpg_dsn(database_url: str) -> str:
    # asyncpg forwards query parameters it does not recognise to the server as session
    # settings. channel_binding is a libpq option, not a server setting, so a Neon-style
    # URL would be rejected at startup. asyncpg cannot do channel binding anyway; sslmode
    # is kept and still enforced. URLs without a query string are returned unchanged.
    parts = urlsplit(database_url)
    if not parts.query:
        return database_url
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != "channel_binding"
    ]
    return urlunsplit(parts._replace(query=urlencode(query)))


async def check_database(settings: Settings) -> bool:
    connection = await asyncpg.connect(
        _asyncpg_dsn(settings.database_url), timeout=settings.database_timeout_seconds
    )
    try:
        await connection.execute("SELECT 1")
        return True
    finally:
        await connection.close()


async def check_cache(settings: Settings) -> bool:
    client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.cache_timeout_seconds,
        socket_timeout=settings.cache_timeout_seconds,
    )
    try:
        return bool(await client.ping())
    finally:
        await client.aclose()


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
