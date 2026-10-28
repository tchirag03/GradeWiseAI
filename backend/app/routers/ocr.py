"""
OCR processing API routes.
Returns transcribed handwritten text stored in MongoDB sheets
produced by the Unified VLM pipeline.
"""
import uuid
from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.mongodb import get_database
from app.schemas.common import (
    OCRStartResponse,
    OCRStatusResponse,
    OCRProgress,
    OCRResultResponse,
    OCRResultDetail,
)

router = APIRouter(tags=["OCR"])


# ---------------------------------------------------------------------------
# POST  /evaluations/{evaluation_id}/ocr/start  —  Unified VLM redirect
# ---------------------------------------------------------------------------
@router.post(
    "/evaluations/{evaluation_id}/ocr/start",
    response_model=OCRStartResponse,
)
async def start_ocr(evaluation_id: str):
    """Start extraction for sheets in this evaluation.
    In the Unified VLM architecture, transcription and grading run together via the Unified Pipeline.
    """
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    sheets = await db.sheets.find({"evaluation_id": evaluation_id}).to_list(length=None)
    total = len(sheets)

    return OCRStartResponse(
        success=True,
        job_id=str(uuid.uuid4()),
        message=f"Evaluation {evaluation_id} uses Unified VLM pipeline. Trigger via /api/evaluations/{evaluation_id}/pipeline/start",
        total_sheets=total,
    )


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}/ocr/status  —  poll progress
# ---------------------------------------------------------------------------
@router.get(
    "/evaluations/{evaluation_id}/ocr/status",
    response_model=OCRStatusResponse,
)
async def get_ocr_status(evaluation_id: str):
    """Get transcription / OCR status for an evaluation from sheets."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    sheets = await db.sheets.find({"evaluation_id": evaluation_id}).to_list(length=None)
    total = len(sheets)
    if total == 0:
        return OCRStatusResponse(
            status="pending",
            progress=OCRProgress(total=0, completed=0, failed=0, percentage=0),
        )

    completed = sum(1 for s in sheets if s.get("ocr_text") or s.get("status") in ("evaluation-completed", "review-needed"))
    failed = sum(1 for s in sheets if s.get("status") == "failed")
    in_progress = sum(1 for s in sheets if s.get("status") in ("processing", "ocr-processing", "transcribing-processing", "preprocessing-processing"))
    pct = round((completed + failed) / total * 100) if total > 0 else 0

    if completed == total and total > 0:
        status = "completed"
    elif failed == total and total > 0:
        status = "failed"
    elif in_progress > 0 or (completed > 0 and completed + failed < total):
        status = "running"
    elif failed > 0:
        status = "failed"
    else:
        status = "pending"

    return OCRStatusResponse(
        status=status,
        progress=OCRProgress(
            total=total,
            completed=completed,
            failed=failed,
            percentage=pct,
        ),
    )


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}/ocr/result/{sheet_id}
# ---------------------------------------------------------------------------
@router.get(
    "/evaluations/{evaluation_id}/ocr/result/{sheet_id}",
    response_model=OCRResultResponse,
)
async def get_ocr_result(evaluation_id: str, sheet_id: str):
    """Get extracted OCR text for a specific sheet."""
    if not ObjectId.is_valid(evaluation_id) or not ObjectId.is_valid(sheet_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    db = get_database()
    doc = await db.sheets.find_one(
        {"_id": ObjectId(sheet_id), "evaluation_id": evaluation_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Sheet not found")

    status = doc.get("status", "uploaded")

    if doc.get("ocr_text"):
        return OCRResultResponse(
            sheet_id=sheet_id,
            status="completed",
            result=OCRResultDetail(
                extracted_text=doc.get("ocr_text", "").strip(),
                confidence=doc.get("ocr_confidence", 1.0),
                processing_time=doc.get("ocr_processing_time_ms", 0),
            ),
        )
    elif status == "failed":
        return OCRResultResponse(
            sheet_id=sheet_id,
            status="failed",
            error=doc.get("error", "Extraction failed"),
        )
    elif status in ("processing", "ocr-processing", "transcribing-processing"):
        return OCRResultResponse(sheet_id=sheet_id, status="running")
    else:
        return OCRResultResponse(sheet_id=sheet_id, status="pending")
