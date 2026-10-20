"""
Student repository — CRUD operations on the students collection.
"""
from app.core.mongodb import get_database


def _col():
    return get_database()["students"]


async def insert_student(name: str) -> dict:
    """Insert a new student document."""
    doc = {"name": name}
    result = await _col().insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


async def get_student(student_id: str) -> dict | None:
    """Fetch a student by _id string."""
    from bson import ObjectId
    doc = await _col().find_one({"_id": ObjectId(student_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def list_students(skip: int = 0, limit: int = 50) -> tuple[list[dict], int]:
    """Paginated listing."""
    col = _col()
    total = await col.count_documents({})
    cursor = col.find().skip(skip).limit(limit)
    docs = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        docs.append(doc)
    return docs, total


async def delete_student(student_id: str) -> bool:
    from bson import ObjectId
    result = await _col().delete_one({"_id": ObjectId(student_id)})
    return result.deleted_count == 1
