"""
MongoDB aggregation pipelines for analytics.
Queries evaluated sheets (primary pipeline) with fallback to scripts (legacy).
All heavy queries live here — no aggregation logic in repositories.
"""
from app.core.mongodb import get_database


def _db():
    return get_database()


async def avg_marks_per_question() -> list[dict]:
    """
    Group by question, compute $avg on awarded score.
    Queries primary evaluated sheets first, falls back to scripts collection.
    """
    db = _db()

    # 1. Primary pipeline: sheets collection
    sheets_pipeline = [
        {
            "$match": {
                "status": {"$in": ["evaluation-completed", "review-needed"]},
                "evaluation_result.questions": {"$exists": True},
            }
        },
        {"$unwind": "$evaluation_result.questions"},
        {
            "$group": {
                "_id": {
                    "$ifNull": [
                        "$evaluation_result.questions.question_text",
                        "Question 1",
                    ]
                },
                "average": {"$avg": "$evaluation_result.questions.total_marks"},
            }
        },
        {"$project": {"question_id": "$_id", "average": {"$round": ["$average", 2]}, "_id": 0}},
        {"$sort": {"question_id": 1}},
    ]
    results = [doc async for doc in db["sheets"].aggregate(sheets_pipeline)]
    if results:
        return results

    # 2. Fallback: scripts collection
    scripts_pipeline = [
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
    return [doc async for doc in db["scripts"].aggregate(scripts_pipeline)]


async def weakest_rubric_components(limit: int = 5) -> list[dict]:
    """
    Unwind evaluation steps/components, group by component name,
    compute average marks, then sort ascending (weakest first).
    """
    db = _db()

    # 1. Primary pipeline: sheets collection
    sheets_pipeline = [
        {
            "$match": {
                "status": {"$in": ["evaluation-completed", "review-needed"]},
                "evaluation_result.questions": {"$exists": True},
            }
        },
        {"$unwind": "$evaluation_result.questions"},
        {"$unwind": "$evaluation_result.questions.component_scores"},
        {
            "$group": {
                "_id": "$evaluation_result.questions.component_scores.component",
                "average_marks": {"$avg": "$evaluation_result.questions.component_scores.marks_awarded"},
            }
        },
        {"$project": {"component": "$_id", "average_marks": {"$round": ["$average_marks", 2]}, "_id": 0}},
        {"$sort": {"average_marks": 1}},
        {"$limit": limit},
    ]
    results = [doc async for doc in db["sheets"].aggregate(sheets_pipeline)]
    if results:
        return results

    # 2. Fallback: scripts collection
    scripts_pipeline = [
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
    return [doc async for doc in db["scripts"].aggregate(scripts_pipeline)]


async def top_students(limit: int = 10) -> list[dict]:
    """
    Group by student, sum evaluation totals, sort descending.
    """
    db = _db()

    # 1. Primary pipeline: sheets collection
    sheets_pipeline = [
        {
            "$match": {
                "status": {"$in": ["evaluation-completed", "review-needed"]},
                "total_score": {"$exists": True},
            }
        },
        {
            "$group": {
                "_id": "$student_name",
                "total": {"$sum": "$total_score"},
            }
        },
        {"$project": {"student_id": "$_id", "total": {"$round": ["$total", 2]}, "_id": 0}},
        {"$sort": {"total": -1}},
        {"$limit": limit},
    ]
    results = [doc async for doc in db["sheets"].aggregate(sheets_pipeline)]
    if results:
        return results

    # 2. Fallback: scripts collection
    scripts_pipeline = [
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
    return [doc async for doc in db["scripts"].aggregate(scripts_pipeline)]


async def student_performance_report(student_id: str) -> dict:
    """
    Per-student breakdown: total scripts, average score, per-question detail.
    """
    db = _db()

    # 1. Primary pipeline: sheets collection
    sheets_pipeline = [
        {
            "$match": {
                "student_name": student_id,
                "status": {"$in": ["evaluation-completed", "review-needed"]},
            }
        },
        {
            "$group": {
                "_id": "$student_name",
                "total_scripts": {"$sum": 1},
                "average_score": {"$avg": "$total_score"},
                "breakdown": {
                    "$push": {
                        "file_name": "$file_name",
                        "total": "$total_score",
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
    results = [doc async for doc in db["sheets"].aggregate(sheets_pipeline)]
    if results:
        return results[0]

    # 2. Fallback: scripts collection
    scripts_pipeline = [
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
    results = [doc async for doc in db["scripts"].aggregate(scripts_pipeline)]
    if results:
        return results[0]

    return {
        "student_id": student_id,
        "total_scripts": 0,
        "average_score": 0.0,
        "breakdown": [],
    }
