"""
Index management for all MongoDB collections.
Provides ensure_indexes (startup) and safe benchmark comparison.
"""
import time
from app.core.mongodb import get_database


SCRIPTS_INDEX_DEFINITIONS = [
    ("student_id", 1),
    ("question_id", 1),
    ("evaluation.total", -1),
    ("created_at", -1),
    ("status", 1),
]

SHEETS_INDEX_DEFINITIONS = [
    [("evaluation_id", 1)],
    [("evaluation_id", 1), ("status", 1)],
    [("evaluation_id", 1), ("needs_human_review", 1)],
    [("status", 1)],
]

EVALUATIONS_INDEX_DEFINITIONS = [
    [("created_at", -1)],
]

RUBRICS_INDEX_DEFINITIONS = [
    [("evaluation_id", 1)],
]


async def ensure_indexes() -> list[str]:
    """Create all required indexes across collections. Idempotent — safe to call on every startup."""
    db = get_database()
    created = []

    # 1. Scripts collection
    col_scripts = db["scripts"]
    for field, direction in SCRIPTS_INDEX_DEFINITIONS:
        name = await col_scripts.create_index([(field, direction)])
        created.append(f"scripts.{name}")

    # 2. Sheets collection
    col_sheets = db["sheets"]
    for idx_def in SHEETS_INDEX_DEFINITIONS:
        name = await col_sheets.create_index(idx_def)
        created.append(f"sheets.{name}")

    # 3. Evaluations collection
    col_evals = db["evaluations"]
    for idx_def in EVALUATIONS_INDEX_DEFINITIONS:
        name = await col_evals.create_index(idx_def)
        created.append(f"evaluations.{name}")

    # 4. Rubrics collection
    col_rubrics = db["rubrics"]
    for idx_def in RUBRICS_INDEX_DEFINITIONS:
        name = await col_rubrics.create_index(idx_def)
        created.append(f"rubrics.{name}")

    print(f"[Indexes] Ensured {len(created)} indexes across collections.")
    return created


async def compare_query_time(query_filter: dict | None = None) -> dict:
    """
    Safely compare indexed vs unindexed query performance
    using an isolated temporary benchmark collection.
    NEVER drops production indexes.
    """
    db = get_database()
    bench_col = db["_benchmark_test"]

    # Seed temporary documents if collection is empty
    count = await bench_col.count_documents({})
    if count < 500:
        docs = [
            {"student_id": f"S{i % 20}", "question_id": f"Q{i % 5}", "score": i * 0.5}
            for i in range(500)
        ]
        await bench_col.insert_many(docs)

    test_filter = query_filter or {"student_id": "S1"}

    # 1. Without index (drop only benchmark collection indexes)
    await bench_col.drop_indexes()
    start = time.perf_counter()
    await bench_col.find(test_filter).to_list(length=100)
    without_index = round(time.perf_counter() - start, 6)

    # 2. With index on benchmark collection
    await bench_col.create_index([("student_id", 1)])
    start = time.perf_counter()
    await bench_col.find(test_filter).to_list(length=100)
    with_index = round(time.perf_counter() - start, 6)

    # Clean up benchmark collection indexes
    try:
        await bench_col.drop()
    except Exception:
        pass

    return {
        "query": str(test_filter),
        "with_index_sec": with_index,
        "without_index_sec": without_index,
        "speedup": round(without_index / with_index, 2) if with_index > 0 else 1.0,
    }
