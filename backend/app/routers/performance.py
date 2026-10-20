"""
Performance router — benchmarking endpoints for demo purposes.
Index comparison, cache comparison, queue throughput.
"""
import time
import asyncio
from fastapi import APIRouter
from app.db.queries import index_setup, aggregation_queries
from app.db.services import cache_service, queue_service

router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get("/index-comparison")
async def index_comparison():
    """Compare query time with vs without indexes."""
    result = await index_setup.compare_query_time()
    return result


@router.get("/cache-comparison")
async def cache_comparison():
    """Compare response time for cached vs uncached analytics query."""
    # Invalidate cache first
    await cache_service.invalidate("analytics:avg_marks")

    # Uncached
    start = time.perf_counter()
    data = await aggregation_queries.avg_marks_per_question()
    uncached_time = round(time.perf_counter() - start, 6)

    # Store in cache
    await cache_service.set_cached("analytics:avg_marks", data, ttl=120)

    # Cached
    start = time.perf_counter()
    await cache_service.get_cached("analytics:avg_marks")
    cached_time = round(time.perf_counter() - start, 6)

    return {
        "uncached_sec": uncached_time,
        "cached_sec": cached_time,
        "speedup": round(uncached_time / cached_time, 2) if cached_time > 0 else None,
        "cache_stats": await cache_service.get_cache_stats(),
    }


@router.get("/queue-throughput")
async def queue_throughput():
    """Measure jobs/sec by enqueuing and dequeuing 50 test jobs."""
    from app.db.services.status_service import set_job_status
    count = 50

    # Enqueue phase
    start = time.perf_counter()
    job_ids = []
    for _ in range(count):
        jid = await queue_service.enqueue_job("test_script", "test_rubric")
        job_ids.append(jid)
    enqueue_time = round(time.perf_counter() - start, 6)

    # Dequeue phase (drain without processing)
    start = time.perf_counter()
    drained = 0
    for _ in range(count):
        job = await queue_service.dequeue_job()
        if job:
            drained += 1
    dequeue_time = round(time.perf_counter() - start, 6)

    return {
        "enqueued": count,
        "drained": drained,
        "enqueue_sec": enqueue_time,
        "dequeue_sec": dequeue_time,
        "enqueue_rate_per_sec": round(count / enqueue_time, 1) if enqueue_time > 0 else None,
        "dequeue_rate_per_sec": round(drained / dequeue_time, 1) if dequeue_time > 0 else None,
    }
