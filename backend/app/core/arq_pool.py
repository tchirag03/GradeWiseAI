"""
Arq Redis connection pool management.
Provides connection pooling for enqueueing offline pipeline tasks.
"""
from typing import Optional
from app.core.config import settings

_arq_pool = None


async def get_arq_redis_settings():
    try:
        from arq.connections import RedisSettings
        return RedisSettings(host=settings.redis_host, port=settings.redis_port)
    except ImportError:
        return None


async def connect_arq_pool():
    """Initialise the Arq Redis pool."""
    global _arq_pool
    try:
        from arq.connections import create_pool, RedisSettings
        redis_settings = RedisSettings(host=settings.redis_host, port=settings.redis_port)
        _arq_pool = await create_pool(redis_settings)
        print(f"[Arq] Connected to Redis queue pool → {settings.redis_host}:{settings.redis_port}")
        return _arq_pool
    except Exception as exc:
        print(f"[Arq] ⚠ Could not connect to Arq Redis pool ({exc}).")
        _arq_pool = None
        return None


async def close_arq_pool():
    """Close the Arq Redis pool on shutdown."""
    global _arq_pool
    if _arq_pool:
        await _arq_pool.close()
        _arq_pool = None
        print("[Arq] Connection pool closed.")


def get_arq_pool():
    """Return active Arq Redis pool instance or None."""
    return _arq_pool
