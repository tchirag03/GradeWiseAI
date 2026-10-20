"""
Unified Pipeline Router for the 5-Stage Offline Evaluation System.
Replaces separate manual stages with an automated, queue-backed flow:
  Stage 0 (Preprocess & Crop) -> Stage 1 (Transcribe) -> Stage 2 (Diagrams) ->
  Stage 3 (Batch Question-Grading) -> Stage 4 (Human Review Flagging).
"""
import asyncio
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.mongodb import get_database
from app.core.arq_pool import get_arq_pool
from app.worker import process_sheet_extraction

router = APIRouter(tags=["Pipeline"])


class PipelineStartResponse(BaseModel):
    success: bool
    evaluation_id: str
    total_sheets: int
    message: str


class PipelineStatusResponse(BaseModel):
    evaluation_id: str
    status: str
    pipeline_stage: str
    total_sheets: int
    completed_sheets: int
    needs_review_count: int
    progress_percentage: int


@router.post("/evaluations/{evaluation_id}/pipeline/start", response_model=PipelineStartResponse)
async def start_pipeline(evaluation_id: str):
    """
    Kicks off the offline evaluation pipeline for all uploaded sheets.
    Enqueues tasks in the Arq Redis worker queue.
    """
    db = get_database()
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    sheets = await db.sheets.find({"evaluation_id": evaluation_id}).to_list(length=None)
    if not sheets:
        raise HTTPException(status_code=400, detail="No sheets uploaded for this evaluation.")

    sheet_ids = [str(s["_id"]) for s in sheets]

    # Set initial pipeline status
    await db.evaluations.update_one(
        {"_id": ObjectId(evaluation_id)},
        {"$set": {"status": "processing", "pipeline_stage": "extraction"}}
    )

    await db.sheets.update_many(
        {"_id": {"$in": [s["_id"] for s in sheets]}},
        {"$set": {"status": "preprocessing-pending"}}
    )

    arq_pool = get_arq_pool()
    if arq_pool:
        # Enqueue via Redis worker queue
        for s_id in sheet_ids:
            await arq_pool.enqueue_job("process_sheet_extraction", evaluation_id, s_id)
        mode = "Arq Redis Worker Queue"
    else:
        # Standalone async fallback if Redis queue worker isn't active
        for s_id in sheet_ids:
            asyncio.create_task(process_sheet_extraction(None, evaluation_id, s_id))
        mode = "In-Process Async Worker"

    return PipelineStartResponse(
        success=True,
        evaluation_id=evaluation_id,
        total_sheets=len(sheets),
        message=f"Offline evaluation pipeline started for {len(sheets)} sheets via {mode}."
    )


@router.get("/evaluations/{evaluation_id}/pipeline/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(evaluation_id: str):
    """
    Polls the progress of the 5-stage offline pipeline.
    """
    db = get_database()
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    sheets = await db.sheets.find({"evaluation_id": evaluation_id}).to_list(length=None)
    total = len(sheets)
    if total == 0:
        return PipelineStatusResponse(
            evaluation_id=evaluation_id,
            status="empty",
            pipeline_stage="idle",
            total_sheets=0,
            completed_sheets=0,
            needs_review_count=0,
            progress_percentage=0,
        )

    completed = sum(1 for s in sheets if s.get("status") in ("evaluation-completed", "review-needed"))
    needs_review = sum(1 for s in sheets if s.get("needs_human_review", False))

    pct = round((completed / total) * 100) if total > 0 else 0

    return PipelineStatusResponse(
        evaluation_id=evaluation_id,
        status=evaluation.get("status", "draft"),
        pipeline_stage=evaluation.get("pipeline_stage", "idle"),
        total_sheets=total,
        completed_sheets=completed,
        needs_review_count=needs_review,
        progress_percentage=pct,
    )
