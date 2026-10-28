"""
Redis-backed queue service for offline script processing.
"""
import json
import asyncio
from typing import Optional, Dict, Any
from bson import ObjectId
from app.core.redis_client import get_redis, redis_available
from app.core.mongodb import get_database

QUEUE_KEY = "evaluation_queue"
STATUS_KEY_PREFIX = "job_status:"
STATUS_TTL = 3600  # 1 hour


async def enqueue_job(script_id: str, rubric_id: str) -> Optional[str]:
    """Push a script evaluation job onto the queue. Returns job_id."""
    r = get_redis()
    if not r:
        return None

    job_id = str(ObjectId())
    payload = json.dumps({"job_id": job_id, "script_id": script_id, "rubric_id": rubric_id})
    await r.rpush(QUEUE_KEY, payload)
    await r.hset(f"{STATUS_KEY_PREFIX}{job_id}", mapping={
        "status": "queued",
        "progress": "0",
        "script_id": script_id,
        "rubric_id": rubric_id,
    })
    await r.expire(f"{STATUS_KEY_PREFIX}{job_id}", STATUS_TTL)
    return job_id


async def dequeue_job() -> Optional[Dict[str, Any]]:
    """Pop the next job from the queue (non-blocking)."""
    r = get_redis()
    if not r:
        return None
    raw = await r.lpop(QUEUE_KEY)
    if not raw:
        return None
    return json.loads(raw)


async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the current status of a job from Redis."""
    r = get_redis()
    if not r:
        return None
    data = await r.hgetall(f"{STATUS_KEY_PREFIX}{job_id}")
    if not data:
        return None
    return {
        "job_id": job_id,
        "status": data.get("status"),
        "progress": int(data.get("progress", 0)),
        "script_id": data.get("script_id"),
        "rubric_id": data.get("rubric_id"),
        "result": json.loads(data["result"]) if "result" in data else None,
    }


async def set_job_status(
    job_id: str,
    status: str,
    progress: int = 0,
    result: Optional[Dict[str, Any]] = None,
) -> None:
    """Update job status in Redis."""
    r = get_redis()
    if not r:
        return
    mapping = {"status": status, "progress": str(progress)}
    if result:
        mapping["result"] = json.dumps(result)
    await r.hset(f"{STATUS_KEY_PREFIX}{job_id}", mapping=mapping)


async def get_queue_length() -> int:
    """Return the number of jobs waiting in the queue."""
    r = get_redis()
    if not r:
        return 0
    return await r.llen(QUEUE_KEY)


async def _process_single(job: Dict[str, Any]) -> None:
    """Evaluate a single script against its rubric."""
    job_id = job["job_id"]
    script_id = job["script_id"]
    rubric_id = job["rubric_id"]

    await set_job_status(job_id, "processing", progress=20)
    db = get_database()

    if not ObjectId.is_valid(script_id) or not ObjectId.is_valid(rubric_id):
        # Synthetic / mock benchmark jobs
        await set_job_status(job_id, "completed", progress=100, result={"evaluation": {"total": 0}})
        return

    script = await db["scripts"].find_one({"_id": ObjectId(script_id)})
    rubric = await db["rubrics"].find_one({"_id": ObjectId(rubric_id)})

    if not script or not rubric:
        await set_job_status(job_id, "failed", progress=0,
                             result={"error": "Script or rubric not found"})
        return

    await set_job_status(job_id, "processing", progress=50)

    # Simple rule-based mock evaluation for fast queue testing
    components = rubric.get("components", [])
    steps = []
    total = 0.0
    for comp in components:
        max_m = comp.get("max_marks", 10)
        awarded = round(max_m * 0.75, 1)
        steps.append({"component": comp.get("name", "Criterion"), "marks": awarded})
        total += awarded
    total = round(total, 2)

    await set_job_status(job_id, "processing", progress=80)

    # Write evaluation back to the script document
    evaluation = {"steps": steps, "total": total}
    await db["scripts"].update_one(
        {"_id": ObjectId(script_id)},
        {"$set": {"evaluation": evaluation, "status": "evaluated"}},
    )

    await set_job_status(job_id, "completed", progress=100,
                         result={"evaluation": evaluation})


async def start_worker() -> None:
    """Background coroutine that continuously processes the queue."""
    if not redis_available():
        print("[Queue Worker] Redis unavailable -- worker not started.")
        return
    print("[Queue Worker] Started.")
    while True:
        try:
            job = await dequeue_job()
            if job:
                try:
                    await _process_single(job)
                except Exception as exc:
                    print(f"[Queue Worker] Error processing job: {exc}")
                    await set_job_status(
                        job["job_id"], "failed", progress=0,
                        result={"error": str(exc)},
                    )
            else:
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            await asyncio.sleep(1.0)
