"""
Redis caching service.
Provides get/set/invalidate helpers and a hit/miss stats counter.
Completely isolated from MongoDB logic.
Gracefully degrades when Redis is unavailable.
"""
import json
from app.core.redis_client import get_redis, redis_available

_HITS_KEY = "cache:stats:hits"
_MISSES_KEY = "cache:stats:misses"


async def get_cached(key: str):
    """Return cached JSON value or None (and track hit/miss)."""
    r = get_redis()
    if r is None:
        return None
    raw = await r.get(key)
    if raw is not None:
        await r.incr(_HITS_KEY)
        return json.loads(raw)
    await r.incr(_MISSES_KEY)
    return None


async def set_cached(key: str, data, ttl: int = 300) -> None:
    """Store a JSON-serialisable value with a TTL (seconds)."""
    r = get_redis()
    if r is None:
        return
    await r.set(key, json.dumps(data, default=str), ex=ttl)


async def invalidate(key: str) -> None:
    """Delete a single cache key."""
    r = get_redis()
    if r is None:
        return
    await r.delete(key)


async def invalidate_pattern(pattern: str) -> None:
    """Delete all keys matching a glob pattern (e.g. 'analytics:*')."""
    r = get_redis()
    if r is None:
        return
    cursor = None
    while cursor != 0:
        cursor, keys = await r.scan(cursor=cursor or 0, match=pattern, count=100)
        if keys:
            await r.delete(*keys)


async def get_cache_stats() -> dict:
    """Return cumulative hit/miss counters."""
    r = get_redis()
    if r is None:
        return {"hits": 0, "misses": 0, "total": 0, "hit_rate": 0.0, "redis": "unavailable"}
    hits = int(await r.get(_HITS_KEY) or 0)
    misses = int(await r.get(_MISSES_KEY) or 0)
    total = hits + misses
    return {
        "hits": hits,
        "misses": misses,
        "total": total,
        "hit_rate": round(hits / total, 4) if total else 0.0,
    }
