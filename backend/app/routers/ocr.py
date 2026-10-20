"""
OCR processing API routes.
Runs Mistral OCR text extraction on uploaded answer sheets
and stores results in MongoDB.
"""
import asyncio
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.mongodb import get_database
from app.services.ocr_service import get_ocr_service
from app.services.structuring_service import get_structuring_service
from app.schemas.common import (
    OCRStartResponse,
    OCRStatusResponse,
    OCRProgress,
    OCRResultResponse,
    OCRResultDetail,
)

router = APIRouter(tags=["OCR"])


# ---------------------------------------------------------------------------
# POST  /evaluations/{evaluation_id}/ocr/start  —  kick off OCR
# ---------------------------------------------------------------------------
@router.post(
    "/evaluations/{evaluation_id}/ocr/start",
    response_model=OCRStartResponse,
)
async def start_ocr(evaluation_id: str):
    """Start OCR processing for all uploaded sheets in this evaluation.

    Processing happens **in the background** so the endpoint returns
    immediately with a job_id.  The frontend polls /ocr/status.
    """
    db = get_database()

    # Validate evaluation
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Gather sheets that haven't been OCR'd yet
    sheets = await db.sheets.find(
        {
            "evaluation_id": evaluation_id,
            "status": {"$in": ["uploaded", "ocr-failed"]},
        }
    ).to_list(length=None)

    if not sheets:
        raise HTTPException(
            status_code=400,
            detail="No sheets pending OCR (all may already be processed).",
        )

    job_id = str(uuid.uuid4())
    total = len(sheets)

    # Mark all target sheets as ocr-pending
    sheet_ids = [s["_id"] for s in sheets]
    await db.sheets.update_many(
        {"_id": {"$in": sheet_ids}},
        {
            "$set": {
                "status": "ocr-pending",
                "ocr_job_id": job_id,
                "ocr_started_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )

    # Store job metadata for status polling
    await db.ocr_jobs.insert_one(
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

    # Fire-and-forget background task
    asyncio.create_task(_process_ocr_batch(job_id, evaluation_id, sheets))

    return OCRStartResponse(
        success=True,
        job_id=job_id,
        message=f"OCR started for {total} sheet(s)",
        total_sheets=total,
    )


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------
async def _process_ocr_batch(
    job_id: str,
    evaluation_id: str,
    sheets: list[dict],
) -> None:
    """Process each sheet through Mistral OCR sequentially in a background task."""
    db = get_database()
    ocr = get_ocr_service()
    completed = 0
    failed = 0

    for sheet in sheets:
        sheet_id = sheet["_id"]
        file_path = sheet["file_path"]

        try:
            # Mark sheet as processing
            await db.sheets.update_one(
                {"_id": sheet_id},
                {"$set": {"status": "ocr-processing"}},
            )

            # Run Mistral OCR call in a thread so we don't block the event loop
            result = await asyncio.to_thread(ocr.extract_text, file_path)

            # Store result on the sheet document
            await db.sheets.update_one(
                {"_id": sheet_id},
                {
                    "$set": {
                        "status": "ocr-completed",
                        "ocr_text": result["text"],
                        "ocr_confidence": result["confidence"],
                        "ocr_processing_time_ms": result["processing_time_ms"],
                        "ocr_completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
            completed += 1

        except Exception as exc:
            await db.sheets.update_one(
                {"_id": sheet_id},
                {"$set": {"status": "ocr-failed", "ocr_error": str(exc)}},
            )
            failed += 1

        # Update job progress after each sheet
        await db.ocr_jobs.update_one(
            {"_id": job_id},
            {"$set": {"completed": completed, "failed": failed}},
        )

    # Mark job finished
    final_status = "completed" if failed == 0 else "failed"
    await db.ocr_jobs.update_one(
        {"_id": job_id},
        {
            "$set": {
                "status": final_status,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}/ocr/status  —  poll progress
# ---------------------------------------------------------------------------
@router.get(
    "/evaluations/{evaluation_id}/ocr/status",
    response_model=OCRStatusResponse,
)
async def get_ocr_status(evaluation_id: str):
    """Get the latest OCR job status for an evaluation."""
    db = get_database()

    # Find the most recent job for this evaluation
    job = await db.ocr_jobs.find_one(
        {"evaluation_id": evaluation_id},
        sort=[("started_at", -1)],
    )

    if not job:
        return OCRStatusResponse(
            status="pending",
            progress=OCRProgress(total=0, completed=0, failed=0, percentage=0),
        )

    total = job["total"]
    completed = job["completed"]
    failed = job["failed"]
    pct = round((completed + failed) / total * 100) if total > 0 else 0

    return OCRStatusResponse(
        status=job["status"],
        progress=OCRProgress(
            total=total,
            completed=completed,
            failed=failed,
            percentage=pct,
        ),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
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
    db = get_database()

    doc = await db.sheets.find_one(
        {"_id": ObjectId(sheet_id), "evaluation_id": evaluation_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Sheet not found")

    status = doc.get("status", "uploaded")

    # Map sheet status to processing status for the response
    if "ocr_text" in doc:
        raw_text = doc.get("ocr_text", "")
        
        # Clean the text for the UI to show what the SLM actually sees (no raw LaTeX)
        try:
            svc = get_structuring_service()
            display_text = svc.clean_ocr_text(raw_text)
        except Exception:
            display_text = raw_text

        return OCRResultResponse(
            sheet_id=sheet_id,
            status="completed",
            result=OCRResultDetail(
                extracted_text=display_text,
                confidence=doc.get("ocr_confidence", -1),
                processing_time=doc.get("ocr_processing_time_ms", 0),
            ),
        )
    elif status == "ocr-failed":
        return OCRResultResponse(
            sheet_id=sheet_id,
            status="failed",
            error=doc.get("ocr_error", "Unknown error"),
        )
    elif status in ("ocr-pending", "ocr-processing"):
        return OCRResultResponse(sheet_id=sheet_id, status="running")
    else:
        return OCRResultResponse(sheet_id=sheet_id, status="pending")
