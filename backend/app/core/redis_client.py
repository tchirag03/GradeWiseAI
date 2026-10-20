"""
Redis async client using redis.asyncio.
Provides lifecycle helpers and client access.
Redis is OPTIONAL — if unavailable the app runs without caching/queue.
"""
import redis.asyncio as aioredis
from app.core.config import settings

_redis: aioredis.Redis | None = None
_available: bool = False


async def connect_redis() -> None:
    """Try to connect to Redis. If it fails, log a warning and continue."""
    global _redis, _available
    try:
        _redis = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )
        await _redis.ping()
        _available = True
        print(f"[Redis] Connected → {settings.redis_host}:{settings.redis_port}")
    except Exception as exc:
        _available = False
        _redis = None
        print(f"[Redis] ⚠ Not available ({exc}). Caching & queue features disabled.")


async def close_redis() -> None:
    """Close the Redis connection if it was established."""
    global _redis, _available
    if _redis:
        await _redis.close()
        _redis = None
        _available = False
        print("[Redis] Connection closed.")


def get_redis() -> aioredis.Redis | None:
    """Return the Redis client, or None if Redis is unavailable."""
    return _redis


def redis_available() -> bool:
    """Check whether Redis is connected."""
    return _available
