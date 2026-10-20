"""
Rubric repository — CRUD operations on the rubrics collection.
"""
from bson import ObjectId
from app.core.mongodb import get_database


def _col():
    return get_database()["rubrics"]


async def insert_rubric(components: list[dict]) -> dict:
    """Insert a new rubric document."""
    doc = {"components": components}
    result = await _col().insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


async def get_rubric(rubric_id: str) -> dict | None:
    """Fetch a rubric by _id."""
    doc = await _col().find_one({"_id": ObjectId(rubric_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def list_rubrics(skip: int = 0, limit: int = 50) -> tuple[list[dict], int]:
    """Paginated listing."""
    col = _col()
    total = await col.count_documents({})
    cursor = col.find().skip(skip).limit(limit)
    docs = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    return docs, total


async def delete_rubric(rubric_id: str) -> bool:
    result = await _col().delete_one({"_id": ObjectId(rubric_id)})
    return result.deleted_count == 1
