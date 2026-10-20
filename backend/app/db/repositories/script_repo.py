"""
Script repository — CRUD operations on the scripts collection.
No business logic; only direct MongoDB interaction.
"""
from datetime import datetime, timezone
from bson import ObjectId
from app.core.mongodb import get_database


def _col():
    return get_database()["scripts"]


async def insert_script(student_id: str, question_id: str, text: str) -> dict:
    """Insert a new answer-script document."""
    doc = {
        "student_id": student_id,
        "question_id": question_id,
        "text": text,
        "evaluation": None,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    }
    result = await _col().insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


async def get_script(script_id: str) -> dict | None:
    """Fetch a single script by its ObjectId."""
    doc = await _col().find_one({"_id": ObjectId(script_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def update_evaluation(script_id: str, evaluation: dict) -> bool:
    """Attach or overwrite the evaluation sub-document."""
    result = await _col().update_one(
        {"_id": ObjectId(script_id)},
        {"$set": {"evaluation": evaluation, "status": "evaluated"}},
    )
    return result.modified_count == 1


async def list_scripts(skip: int = 0, limit: int = 20) -> tuple[list[dict], int]:
    """Paginated listing. Returns (docs, total_count)."""
    col = _col()
    total = await col.count_documents({})
    cursor = col.find().skip(skip).limit(limit).sort("created_at", -1)
    docs = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    return docs, total


async def delete_script(script_id: str) -> bool:
    """Remove a script by ObjectId."""
    result = await _col().delete_one({"_id": ObjectId(script_id)})
    return result.deleted_count == 1
