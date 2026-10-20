"""
Text structuring API routes.
Parses raw OCR text into structured Q&A format and stores results in MongoDB.
"""
import asyncio
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.mongodb import get_database
from app.services.structuring_service import get_structuring_service
from app.schemas.structuring import (
    StructuringStartResponse,
    StructuringStatusResponse,
    StructuringProgress,
    StructuringResultResponse,
    StructuredText,
    StructuredTextMetadata,
    StructuredQuestion,
    StructuredAnswer,
)

router = APIRouter(tags=["Structuring"])


# ---------------------------------------------------------------------------
# POST  /evaluations/{evaluation_id}/structuring/start
# ---------------------------------------------------------------------------
@router.post(
    "/evaluations/{evaluation_id}/structuring/start",
    response_model=StructuringStartResponse,
)
async def start_structuring(evaluation_id: str):
    """Start text structuring for all OCR-completed sheets.

    Runs in the background; frontend polls /structuring/status.
    """
    db = get_database()

    # Validate evaluation
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Gather sheets that have OCR text but haven't been structured yet
    sheets = await db.sheets.find(
        {
            "evaluation_id": evaluation_id,
            "status": {"$in": ["ocr-completed", "structuring-failed"]},
        }
    ).to_list(length=None)

    if not sheets:
        raise HTTPException(
            status_code=400,
            detail="No OCR-completed sheets to structure. Run OCR first.",
        )

    job_id = str(uuid.uuid4())
    total = len(sheets)

    # Mark sheets as pending
    sheet_ids = [s["_id"] for s in sheets]
    await db.sheets.update_many(
        {"_id": {"$in": sheet_ids}},
        {
            "$set": {
                "status": "structuring-pending",
                "structuring_job_id": job_id,
            }
        },
    )

    # Create job record
    await db.structuring_jobs.insert_one(
        {
            "_id": job_id,
            "evaluation_id": evaluation_id,
            "total": total,
            "completed": 0,
            "failed": 0,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
    )

    # Background processing
    asyncio.create_task(_process_structuring_batch(job_id, evaluation_id, sheets))

    return StructuringStartResponse(
        success=True,
        job_id=job_id,
        message=f"Structuring started for {total} sheet(s)",
        total_sheets=total,
    )


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------
async def _process_structuring_batch(
    job_id: str,
    evaluation_id: str,
    sheets: list[dict],
) -> None:
    """Structure each sheet's OCR text sequentially in the background."""
    db = get_database()
    svc = get_structuring_service()
    completed = 0
    failed = 0

    for sheet in sheets:
        sheet_id = sheet["_id"]
        raw_text = sheet.get("ocr_text", "")

        try:
            await db.sheets.update_one(
                {"_id": sheet_id},
                {"$set": {"status": "structuring-processing"}},
            )

            # Structuring is CPU-light but run in thread for consistency
            result = await asyncio.to_thread(svc.structure_text, raw_text)

            await db.sheets.update_one(
                {"_id": sheet_id},
                {
                    "$set": {
                        "status": "structuring-completed",
                        "structured_data": result,
                        "structuring_completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
            completed += 1

        except Exception as exc:
            await db.sheets.update_one(
                {"_id": sheet_id},
                {
                    "$set": {
                        "status": "structuring-failed",
                        "structuring_error": str(exc),
                    }
                },
            )
            failed += 1

        # Update job progress
        await db.structuring_jobs.update_one(
            {"_id": job_id},
            {"$set": {"completed": completed, "failed": failed}},
        )

    # Finalise job
    final_status = "completed" if failed == 0 else "failed"
    await db.structuring_jobs.update_one(
        {"_id": job_id},
        {
            "$set": {
                "status": final_status,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}/structuring/status
# ---------------------------------------------------------------------------
@router.get(
    "/evaluations/{evaluation_id}/structuring/status",
    response_model=StructuringStatusResponse,
)
async def get_structuring_status(evaluation_id: str):
    """Get the latest structuring job status."""
    db = get_database()

    job = await db.structuring_jobs.find_one(
        {"evaluation_id": evaluation_id},
        sort=[("started_at", -1)],
    )

    if not job:
        return StructuringStatusResponse(
            status="pending",
            progress=StructuringProgress(total=0, completed=0, failed=0, percentage=0),
        )

    total = job["total"]
    completed = job["completed"]
    failed = job["failed"]
    pct = round((completed + failed) / total * 100) if total > 0 else 0

    return StructuringStatusResponse(
        status=job["status"],
        progress=StructuringProgress(
            total=total,
            completed=completed,
            failed=failed,
            percentage=pct,
        ),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
    )


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}/structuring/result/{sheet_id}
# ---------------------------------------------------------------------------
@router.get(
    "/evaluations/{evaluation_id}/structuring/result/{sheet_id}",
    response_model=StructuringResultResponse,
)
async def get_structuring_result(evaluation_id: str, sheet_id: str):
    """Get structured text result for a specific sheet."""
    db = get_database()

    doc = await db.sheets.find_one(
        {"_id": ObjectId(sheet_id), "evaluation_id": evaluation_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Sheet not found")

    status = doc.get("status", "uploaded")

    if status == "structuring-completed":
        data = doc.get("structured_data", {})
        return StructuringResultResponse(
            sheet_id=sheet_id,
            status="completed",
            result=StructuredText(
                questions=[
                    StructuredQuestion(
                        question_number=q["question_number"],
                        question_text=q["question_text"],
                        answer=StructuredAnswer(**q["answer"]),
                    )
                    for q in data.get("questions", [])
                ],
                metadata=StructuredTextMetadata(**data.get("metadata", {
                    "total_questions": 0,
                    "total_steps": 0,
                    "average_complexity": "N/A",
                })),
            ),
        )
    elif status == "structuring-failed":
        return StructuringResultResponse(
            sheet_id=sheet_id,
            status="failed",
            error=doc.get("structuring_error", "Unknown error"),
        )
    elif status in ("structuring-pending", "structuring-processing"):
        return StructuringResultResponse(sheet_id=sheet_id, status="running")
    else:
        return StructuringResultResponse(sheet_id=sheet_id, status="pending")
