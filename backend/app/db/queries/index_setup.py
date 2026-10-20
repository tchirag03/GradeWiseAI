"""
Index management for the scripts collection.
Provides ensure_indexes (startup), drop_indexes, and compare_query_time for benchmarking.
"""
import time
from app.core.mongodb import get_database


INDEX_DEFINITIONS = [
    ("student_id", 1),
    ("question_id", 1),
    ("evaluation.total", -1),
    ("created_at", -1),
    ("status", 1),
]


async def ensure_indexes() -> list[str]:
    """Create all required indexes. Idempotent — safe to call on every startup."""
    col = get_database()["scripts"]
    created = []
    for field, direction in INDEX_DEFINITIONS:
        name = await col.create_index([(field, direction)])
        created.append(name)
    print(f"[Indexes] Ensured {len(created)} indexes on 'scripts'.")
    return created


async def drop_indexes() -> None:
    """Drop all non-_id indexes on the scripts collection."""
    col = get_database()["scripts"]
    await col.drop_indexes()
    print("[Indexes] Dropped all non-_id indexes on 'scripts'.")


async def compare_query_time(query_filter: dict | None = None) -> dict:
    """
    Run the same query with and without indexes, return elapsed times.
    Used for the benchmarking / performance demo.
    """
    col = get_database()["scripts"]
    if query_filter is None:
        query_filter = {"student_id": "S1"}

    # --- With indexes ---
    await ensure_indexes()
    start = time.perf_counter()
    await col.find(query_filter).to_list(length=100)
    with_index = round(time.perf_counter() - start, 6)

    # --- Without indexes ---
    await drop_indexes()
    start = time.perf_counter()
    await col.find(query_filter).to_list(length=100)
    without_index = round(time.perf_counter() - start, 6)

    # Restore indexes for normal operation
    await ensure_indexes()

    return {
        "query": str(query_filter),
        "with_index_sec": with_index,
        "without_index_sec": without_index,
        "speedup": round(without_index / with_index, 2) if with_index > 0 else None,
    }
