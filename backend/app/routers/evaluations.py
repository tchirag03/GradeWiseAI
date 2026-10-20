"""
Evaluation management API routes.
Real MongoDB CRUD for evaluations.
"""
import shutil
import os
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.mongodb import get_database
from app.schemas.evaluation import (
    CreateEvaluationRequest,
    EvaluationResponse,
    EvaluationListResponse,
    DeleteEvaluationResponse,
)

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


# ---------------------------------------------------------------------------
# POST  /evaluations  —  create a new evaluation
# ---------------------------------------------------------------------------
@router.post("", response_model=EvaluationResponse)
async def create_evaluation(request: CreateEvaluationRequest):
    """Create a new evaluation and persist it to MongoDB."""
    db = get_database()

    doc = {
        "name": request.name,
        "subject": request.subject,
        "max_marks": request.max_marks,
        "answer_type": request.answer_type,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.evaluations.insert_one(doc)

    return EvaluationResponse(
        id=str(result.inserted_id),
        name=request.name,
        subject=request.subject,
        max_marks=request.max_marks,
        answer_type=request.answer_type,
        status="draft",
    )


# ---------------------------------------------------------------------------
# GET  /evaluations  —  list all evaluations
# ---------------------------------------------------------------------------
@router.get("", response_model=EvaluationListResponse)
async def list_evaluations():
    """List all evaluations from MongoDB."""
    db = get_database()
    cursor = db.evaluations.find().sort("created_at", -1)
    evaluations = []

    async for doc in cursor:
        evaluations.append(
            EvaluationResponse(
                id=str(doc["_id"]),
                name=doc["name"],
                subject=doc.get("subject", ""),
                max_marks=doc.get("max_marks", 0),
                answer_type=doc.get("answer_type", "printed"),
                status=doc.get("status", "draft"),
            )
        )

    return EvaluationListResponse(success=True, evaluations=evaluations)


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}  —  get one evaluation
# ---------------------------------------------------------------------------
@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(evaluation_id: str):
    """Get evaluation by ID from MongoDB."""
    db = get_database()

    try:
        doc = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    if not doc:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return EvaluationResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        subject=doc.get("subject", ""),
        max_marks=doc.get("max_marks", 0),
        answer_type=doc.get("answer_type", "printed"),
        status=doc.get("status", "draft"),
    )


# ---------------------------------------------------------------------------
# DELETE  /evaluations/{evaluation_id}  —  cascade delete evaluation
# ---------------------------------------------------------------------------
@router.delete("/{evaluation_id}", response_model=DeleteEvaluationResponse)
async def delete_evaluation(evaluation_id: str):
    """Delete an evaluation + all its sheets and rubric files."""
    db = get_database()

    try:
        doc = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    if not doc:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Cascade: remove all related sheets and rubrics from MongoDB
    await db.sheets.delete_many({"evaluation_id": evaluation_id})
    await db.rubrics.delete_many({"evaluation_id": evaluation_id})

    # Remove upload directory from disk
    upload_path = os.path.join(settings.upload_dir, evaluation_id)
    if os.path.exists(upload_path):
        shutil.rmtree(upload_path)

    # Delete the evaluation itself
    await db.evaluations.delete_one({"_id": ObjectId(evaluation_id)})

    return DeleteEvaluationResponse(
        success=True,
        deleted=evaluation_id,
        message=f"Evaluation '{doc['name']}' and all related data deleted",
    )
