"""
Redis-backed job queue service.
Uses a Redis List (LPUSH / BRPOP) as a lightweight async job queue.
Gracefully degrades when Redis is unavailable.
"""
import asyncio
import json
import random
import uuid

from app.core.redis_client import get_redis, redis_available
from app.core.mongodb import get_database
from app.db.services.status_service import set_job_status

QUEUE_KEY = "eval:job_queue"


async def enqueue_job(script_id: str, rubric_id: str) -> str:
    """Push an evaluation job onto the queue. Returns the job_id."""
    job_id = str(uuid.uuid4())
    r = get_redis()
    if r is None:
        return job_id  # return id but job won't be processed
    payload = json.dumps({
        "job_id": job_id,
        "script_id": script_id,
        "rubric_id": rubric_id,
    })
    await r.lpush(QUEUE_KEY, payload)
    await set_job_status(job_id, "queued", progress=0)
    return job_id


async def dequeue_job() -> dict | None:
    """Blocking pop a job from the queue (timeout 1 s). Returns parsed dict or None."""
    r = get_redis()
    if r is None:
        return None
    result = await r.brpop(QUEUE_KEY, timeout=1)
    if result:
        _, raw = result
        return json.loads(raw)
    return None


async def _process_single(job: dict) -> None:
    """Simulate evaluating a script against a rubric."""
    job_id = job["job_id"]
    script_id = job["script_id"]
    rubric_id = job["rubric_id"]

    await set_job_status(job_id, "processing", progress=10)

    # Fetch rubric components from Mongo
    from bson import ObjectId
    db = get_database()
    rubric = await db["rubrics"].find_one({"_id": ObjectId(rubric_id)})
    if not rubric:
        await set_job_status(job_id, "failed", progress=0,
                             result={"error": "Rubric not found"})
        return

    await set_job_status(job_id, "processing", progress=40)

    # Simulate scoring each component
    steps = []
    total = 0.0
    for comp in rubric["components"]:
        awarded = round(random.uniform(0, comp["marks"]), 1)
        steps.append({"component": comp["name"], "marks": awarded})
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
        print("[Queue Worker] Redis unavailable — worker not started.")
        return
    print("[Queue Worker] Started.")
    while True:
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
