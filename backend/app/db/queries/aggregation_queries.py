"""
MongoDB aggregation pipelines for analytics.
All heavy queries live here — no aggregation logic in repositories.
"""
from app.core.mongodb import get_database


def _scripts():
    return get_database()["scripts"]


async def avg_marks_per_question() -> list[dict]:
    """
    Group by question_id, compute $avg on evaluation.total.
    Only considers evaluated scripts.
    """
    pipeline = [
        {"$match": {"status": "evaluated"}},
        {
            "$group": {
                "_id": "$question_id",
                "average": {"$avg": "$evaluation.total"},
            }
        },
        {"$project": {"question_id": "$_id", "average": {"$round": ["$average", 2]}, "_id": 0}},
        {"$sort": {"question_id": 1}},
    ]
    return [doc async for doc in _scripts().aggregate(pipeline)]


async def weakest_rubric_components(limit: int = 5) -> list[dict]:
    """
    Unwind evaluation steps, group by component name,
    compute average marks, then sort ascending (weakest first).
    """
    pipeline = [
        {"$match": {"status": "evaluated"}},
        {"$unwind": "$evaluation.steps"},
        {
            "$group": {
                "_id": "$evaluation.steps.component",
                "average_marks": {"$avg": "$evaluation.steps.marks"},
            }
        },
        {"$project": {"component": "$_id", "average_marks": {"$round": ["$average_marks", 2]}, "_id": 0}},
        {"$sort": {"average_marks": 1}},
        {"$limit": limit},
    ]
    return [doc async for doc in _scripts().aggregate(pipeline)]


async def top_students(limit: int = 10) -> list[dict]:
    """
    Group by student_id, sum evaluation totals, sort descending.
    """
    pipeline = [
        {"$match": {"status": "evaluated"}},
        {
            "$group": {
                "_id": "$student_id",
                "total": {"$sum": "$evaluation.total"},
            }
        },
        {"$project": {"student_id": "$_id", "total": {"$round": ["$total", 2]}, "_id": 0}},
        {"$sort": {"total": -1}},
        {"$limit": limit},
    ]
    return [doc async for doc in _scripts().aggregate(pipeline)]


async def student_performance_report(student_id: str) -> dict:
    """
    Per-student breakdown: total scripts, average score, per-question detail.
    """
    pipeline = [
        {"$match": {"student_id": student_id, "status": "evaluated"}},
        {
            "$group": {
                "_id": "$student_id",
                "total_scripts": {"$sum": 1},
                "average_score": {"$avg": "$evaluation.total"},
                "breakdown": {
                    "$push": {
                        "question_id": "$question_id",
                        "total": "$evaluation.total",
                    }
                },
            }
        },
        {
            "$project": {
                "student_id": "$_id",
                "total_scripts": 1,
                "average_score": {"$round": ["$average_score", 2]},
                "breakdown": 1,
                "_id": 0,
            }
        },
    ]
    results = [doc async for doc in _scripts().aggregate(pipeline)]
    if results:
        return results[0]
    return {
        "student_id": student_id,
        "total_scripts": 0,
        "average_score": 0.0,
        "breakdown": [],
    }
