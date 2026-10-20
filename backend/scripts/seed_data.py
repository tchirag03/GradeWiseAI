"""
Seed script — Populates MongoDB with randomized evaluation data.
Creates 50 students, 10 rubrics, and 1000+ scripts with evaluations.

Usage:
    cd c:\\Users\\tchir\\Desktop\\pp1\\backend
    python -m scripts.seed_data
"""
import asyncio
import random
from datetime import datetime, timezone, timedelta

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

COMPONENT_NAMES = [
    "Initialization",
    "Loop Structure",
    "Boundary Handling",
    "Output Formatting",
    "Optimization",
    "Error Handling",
    "Variable Naming",
    "Code Readability",
    "Algorithm Correctness",
    "Edge Cases",
]


async def seed():
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.db_name]

    # Drop existing collections for a clean seed
    for col_name in ("students", "rubrics", "scripts"):
        await db.drop_collection(col_name)
    print("[Seed] Collections cleared.")

    # ------ Students (50) ------
    students = []
    for i in range(1, 51):
        doc = {"name": f"Student_{i:03d}"}
        result = await db["students"].insert_one(doc)
        students.append(str(result.inserted_id))
    print(f"[Seed] Inserted {len(students)} students.")

    # ------ Rubrics (10 — one per question) ------
    rubric_ids = []
    for q in range(1, 11):
        num_components = random.randint(3, 6)
        components = [
            {"name": random.choice(COMPONENT_NAMES), "marks": round(random.uniform(1, 5), 1)}
            for _ in range(num_components)
        ]
        result = await db["rubrics"].insert_one({"components": components})
        rubric_ids.append(str(result.inserted_id))
    print(f"[Seed] Inserted {len(rubric_ids)} rubrics.")

    # ------ Scripts (1 200) ------
    scripts_to_insert = []
    base_time = datetime.now(timezone.utc) - timedelta(days=30)

    for idx in range(1200):
        sid = random.choice(students)
        qid = f"Q{random.randint(1, 10)}"
        # Build evaluation
        rubric_index = int(qid[1:]) - 1
        rubric = await db["rubrics"].find_one({"_id": __import__("bson").ObjectId(rubric_ids[rubric_index])})
        steps = []
        total = 0.0
        for comp in rubric["components"]:
            awarded = round(random.uniform(0, comp["marks"]), 1)
            steps.append({"component": comp["name"], "marks": awarded})
            total += awarded
        total = round(total, 2)

        scripts_to_insert.append({
            "student_id": sid,
            "question_id": qid,
            "text": f"Sample answer text for {qid} by student {sid[:8]}…",
            "evaluation": {"steps": steps, "total": total},
            "status": "evaluated",
            "created_at": base_time + timedelta(minutes=idx * 2),
        })

    await db["scripts"].insert_many(scripts_to_insert)
    print(f"[Seed] Inserted {len(scripts_to_insert)} scripts.")

    client.close()
    print("[Seed] Done ✓")


if __name__ == "__main__":
    asyncio.run(seed())
