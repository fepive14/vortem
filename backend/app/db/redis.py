"""Redis connection pool and dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings

# Single connection pool shared across the application lifetime.
_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=20,
)


def get_redis_client() -> aioredis.Redis:
    """Return a Redis client backed by the shared connection pool."""
    return aioredis.Redis(connection_pool=_pool)


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency that yields a Redis client."""
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()
