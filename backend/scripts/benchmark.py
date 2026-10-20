"""
Benchmark script — Runs timed comparisons for:
  • Indexed vs non-indexed queries
  • Cached vs uncached reads
  • Queue throughput
  • Aggregation speed

Usage:
    cd c:\\Users\\tchir\\Desktop\\pp1\\backend
    python -m scripts.benchmark
"""
import asyncio
import time

from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as aioredis

from app.core.config import settings

# ── We wire up the global singletons so the app modules work ──
import app.core.mongodb as _mongo_mod
import app.core.redis_client as _redis_mod
from app.db.queries import index_setup, aggregation_queries
from app.db.services import cache_service, queue_service


def _banner(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def bench_indexes():
    _banner("INDEX COMPARISON")
    result = await index_setup.compare_query_time({"student_id": {"$regex": "^."}})
    print(f"  With index   : {result['with_index_sec']:.6f} s")
    print(f"  Without index: {result['without_index_sec']:.6f} s")
    print(f"  Speed-up     : {result['speedup']}×")


async def bench_aggregations():
    _banner("AGGREGATION SPEED")

    for name, coro_fn in [
        ("avg_marks_per_question", aggregation_queries.avg_marks_per_question),
        ("top_students(10)", lambda: aggregation_queries.top_students(10)),
        ("weakest_rubric_components(5)", lambda: aggregation_queries.weakest_rubric_components(5)),
    ]:
        start = time.perf_counter()
        await coro_fn()
        elapsed = time.perf_counter() - start
        print(f"  {name:40s} → {elapsed:.6f} s")


async def bench_cache():
    _banner("CACHE COMPARISON")
    key = "bench:avg_marks"
    await cache_service.invalidate(key)

    # Uncached (fresh aggregation)
    start = time.perf_counter()
    data = await aggregation_queries.avg_marks_per_question()
    uncached = time.perf_counter() - start

    await cache_service.set_cached(key, data, ttl=60)

    # Cached
    start = time.perf_counter()
    await cache_service.get_cached(key)
    cached = time.perf_counter() - start

    speedup = round(uncached / cached, 2) if cached > 0 else "∞"
    print(f"  Uncached : {uncached:.6f} s")
    print(f"  Cached   : {cached:.6f} s")
    print(f"  Speed-up : {speedup}×")
    print(f"  Stats    : {await cache_service.get_cache_stats()}")


async def bench_queue():
    _banner("QUEUE THROUGHPUT")
    count = 100

    start = time.perf_counter()
    for _ in range(count):
        await queue_service.enqueue_job("bench_script", "bench_rubric")
    enqueue_time = time.perf_counter() - start

    start = time.perf_counter()
    drained = 0
    for _ in range(count):
        job = await queue_service.dequeue_job()
        if job:
            drained += 1
    dequeue_time = time.perf_counter() - start

    print(f"  Enqueued {count} jobs in {enqueue_time:.4f} s  "
          f"({count / enqueue_time:.0f} jobs/s)")
    print(f"  Drained  {drained} jobs in {dequeue_time:.4f} s  "
          f"({drained / dequeue_time:.0f} jobs/s)")


async def main():
    # Boot connections
    client = AsyncIOMotorClient(settings.mongo_uri)
    _mongo_mod._client = client
    _mongo_mod._db = client[settings.db_name]

    r = aioredis.Redis(host=settings.redis_host, port=settings.redis_port,
                       decode_responses=True)
    _redis_mod._redis = r

    try:
        await bench_indexes()
        await bench_aggregations()
        await bench_cache()
        await bench_queue()
    finally:
        await r.close()
        client.close()

    print(f"\n{'='*60}")
    print("  ALL BENCHMARKS COMPLETE ✓")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
