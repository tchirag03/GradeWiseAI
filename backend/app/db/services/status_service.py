"""
Job status tracking service backed by Redis Hashes.
Status flow: queued → processing → completed → failed
Gracefully degrades when Redis is unavailable.
"""
import json
from typing import Optional
from app.core.redis_client import get_redis

_PREFIX = "job:status:"


async def set_job_status(
    job_id: str,
    status: str,
    progress: int = 0,
    result: Optional[dict] = None,
) -> None:
    """Update the status hash for a given job."""
    r = get_redis()
    if r is None:
        return
    mapping = {
        "status": status,
        "progress": str(progress),
    }
    if result is not None:
        mapping["result"] = json.dumps(result, default=str)
    await r.hset(f"{_PREFIX}{job_id}", mapping=mapping)
    # Auto-expire after 1 hour to avoid unbounded growth
    await r.expire(f"{_PREFIX}{job_id}", 3600)


async def get_job_status(job_id: str) -> dict | None:
    """Read the status hash for a job. Returns None if unknown job_id."""
    r = get_redis()
    if r is None:
        return None
    data = await r.hgetall(f"{_PREFIX}{job_id}")
    if not data:
        return None
    out = {
        "job_id": job_id,
        "status": data.get("status", "unknown"),
        "progress": int(data.get("progress", 0)),
    }
    if "result" in data:
        out["result"] = json.loads(data["result"])
    return out
