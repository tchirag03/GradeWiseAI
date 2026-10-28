"""
Evaluation management API routes.
Real MongoDB CRUD for evaluations.
"""
import shutil
import os
import re
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.mongodb import get_database
from app.core.event_bus import clear_events
from app.schemas.evaluation import (
    CreateEvaluationRequest,
    EvaluationResponse,
    EvaluationListResponse,
    DeleteEvaluationResponse,
)

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


def _is_safe_path(base_dir: str, target_path: str) -> bool:
    try:
        abs_base = os.path.abspath(base_dir)
        abs_target = os.path.abspath(target_path)
        return os.path.commonpath([abs_base]) == os.path.commonpath([abs_base, abs_target])
    except Exception:
        return False


# ---------------------------------------------------------------------------
# POST  /evaluations  —  create a new evaluation
# ---------------------------------------------------------------------------
@router.post("", response_model=EvaluationResponse)
async def create_evaluation(request: CreateEvaluationRequest):
    """Create a new evaluation and persist it to MongoDB."""
    db = get_database()

    doc = {
        "name": request.name.strip(),
        "subject": request.subject.strip(),
        "max_marks": request.max_marks,
        "answer_type": request.answer_type,
        "status": "draft",
        "pipeline_stage": "idle",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.evaluations.insert_one(doc)

    return EvaluationResponse(
        id=str(result.inserted_id),
        name=doc["name"],
        subject=doc["subject"],
        max_marks=doc["max_marks"],
        answer_type=doc["answer_type"],
        status="draft",
        pipeline_stage="idle",
        created_at=doc["created_at"],
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
                name=doc.get("name", ""),
                subject=doc.get("subject", ""),
                max_marks=doc.get("max_marks", 0),
                answer_type=doc.get("answer_type", "printed"),
                status=doc.get("status", "draft"),
                pipeline_stage=doc.get("pipeline_stage", "idle"),
                rubric_id=doc.get("rubric_id"),
                rubric_file=doc.get("rubric_file"),
                created_at=doc.get("created_at"),
            )
        )

    return EvaluationListResponse(success=True, evaluations=evaluations)


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}  —  get one evaluation
# ---------------------------------------------------------------------------
@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(evaluation_id: str):
    """Get evaluation by ID from MongoDB."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    doc = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})

    if not doc:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return EvaluationResponse(
        id=str(doc["_id"]),
        name=doc.get("name", ""),
        subject=doc.get("subject", ""),
        max_marks=doc.get("max_marks", 0),
        answer_type=doc.get("answer_type", "printed"),
        status=doc.get("status", "draft"),
        pipeline_stage=doc.get("pipeline_stage", "idle"),
        rubric_id=doc.get("rubric_id"),
        rubric_file=doc.get("rubric_file"),
        created_at=doc.get("created_at"),
    )


# ---------------------------------------------------------------------------
# DELETE  /evaluations/{evaluation_id}  —  cascade delete evaluation
# ---------------------------------------------------------------------------
@router.delete("/{evaluation_id}", response_model=DeleteEvaluationResponse)
async def delete_evaluation(evaluation_id: str):
    """Delete an evaluation + all its sheets and rubric files."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    doc = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})

    if not doc:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Cascade: remove all related sheets and rubrics from MongoDB
    await db.sheets.delete_many({"evaluation_id": evaluation_id})
    await db.rubrics.delete_many({"evaluation_id": evaluation_id})

    # Clear memory event bus
    clear_events(evaluation_id)

    # Remove upload directory from disk safely
    upload_path = os.path.join(settings.upload_dir, evaluation_id)
    if os.path.exists(upload_path) and _is_safe_path(settings.upload_dir, upload_path):
        try:
            shutil.rmtree(upload_path)
        except OSError:
            pass

    # Remove logs directory from disk safely
    log_path = os.path.join(settings.log_dir, evaluation_id)
    if os.path.exists(log_path) and _is_safe_path(settings.log_dir, log_path):
        try:
            shutil.rmtree(log_path)
        except OSError:
            pass

    # Delete the evaluation itself
    await db.evaluations.delete_one({"_id": ObjectId(evaluation_id)})

    return DeleteEvaluationResponse(
        success=True,
        deleted=evaluation_id,
        message=f"Evaluation '{doc.get('name', evaluation_id)}' and all related data deleted",
    )
