from datetime import datetime, timezone

import asyncpg
from redis.asyncio import Redis

from app.core.config import Settings


async def check_database(settings: Settings) -> bool:
    connection = await asyncpg.connect(
        settings.database_url, timeout=settings.database_timeout_seconds
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
