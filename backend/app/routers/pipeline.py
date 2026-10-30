"""
Unified Pipeline Router for the 5-Stage Offline Evaluation System.
Replaces separate manual stages with an automated, queue-backed flow:
  Stage 0 (Preprocess & Crop) -> Stage 1 (Transcribe) -> Stage 2 (Diagrams) ->
  Stage 3 (Batch Question-Grading) -> Stage 4 (Human Review Flagging).
Stores detailed logs in a dedicated folder for each run:
  logs/{evaluation_id}/{run_id}/run.log
  logs/{evaluation_id}/{run_id}/summary.json
"""
import asyncio
import json
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.mongodb import get_database
from app.core.arq_pool import get_arq_pool
from app.worker import process_sheet_extraction
from app.core.logging_config import (
    get_run_logger,
    list_evaluation_runs,
    read_run_log,
)
from app.core.event_bus import (
    subscribe_events,
    unsubscribe_events,
    get_history,
    publish_event,
)

router = APIRouter(tags=["Pipeline"])


class PipelineStartResponse(BaseModel):
    success: bool
    evaluation_id: str
    run_id: str
    log_folder: str
    total_sheets: int
    message: str


class PipelineStatusResponse(BaseModel):
    evaluation_id: str
    status: str
    pipeline_stage: str
    total_sheets: int
    completed_sheets: int
    failed_sheets: int = 0
    needs_review_count: int
    progress_percentage: int
    errors: list[str] = []
    latest_run_id: str | None = None
    latest_log_dir: str | None = None


@router.post("/evaluations/{evaluation_id}/pipeline/start", response_model=PipelineStartResponse)
async def start_pipeline(evaluation_id: str):
    """
    Kicks off the offline evaluation pipeline for all uploaded sheets.
    Creates a dedicated run folder and enqueues tasks.
    """
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    sheets = await db.sheets.find({"evaluation_id": evaluation_id}).to_list(length=None)
    if not sheets:
        raise HTTPException(status_code=400, detail="No sheets uploaded for this evaluation.")

    # Check that a rubric exists
    rubric = await db.rubrics.find_one({"evaluation_id": evaluation_id})
    if not rubric and not evaluation.get("rubric_id"):
        raise HTTPException(
            status_code=400,
            detail="No rubric uploaded for this evaluation. Please upload a rubric before starting the pipeline."
        )

    sheet_ids = [str(s["_id"]) for s in sheets]

    # Generate unique run ID and dedicated log folder
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp}"
    logger = get_run_logger(evaluation_id, run_id)
    run_dir = getattr(logger, "run_dir", "")
    log_file = getattr(logger, "log_file", "")

    # Pre-flight check: Verify Ollama and model are ready before marking status as processing
    from app.services.unified_vlm_service import get_unified_vlm_service
    vlm_svc = get_unified_vlm_service()
    logger.info("Pre-flight: Checking Ollama model Qwen3-vl:8B (\"Are you up?\")....")
    is_up, ping_latency, ping_reply = await vlm_svc.ping_model()
    if not is_up:
        logger.error("Pre-flight check failed for model '%s': %s", " Qwen3-vl:8B", ping_reply)
        raise HTTPException(
            status_code=503,
            detail=(
                f"Cannot start pipeline: Ollama model '{' Qwen3-vl:8B'}' is not reachable ({ping_reply}). "
                f"Please ensure Ollama is running (`ollama serve`) and model '{" Qwen3-vl:8B"}' is loaded."
            ),
        )
    logger.info("Pre-flight check passed in %.2fs (Ollama runner ready in RAM).", ping_latency)

    # Set initial pipeline status and associate run folder
    await db.evaluations.update_one(
        {"_id": ObjectId(evaluation_id)},
        {
            "$set": {
                "status": "processing",
                "pipeline_stage": "extraction",
                "latest_run_id": run_id,
                "latest_log_dir": run_dir,
                "latest_log_file": log_file,
            }
        },
    )

    await db.sheets.update_many(
        {"_id": {"$in": [s["_id"] for s in sheets]}},
        {"$set": {"status": "preprocessing-pending", "error": None}}
    )

    # Process sheets sequentially in-process so local CPU is not overwhelmed
    # and execution begins immediately without requiring a separate external worker process.
    async def _run_sequential():
        for s_id in sheet_ids:
            try:
                await process_sheet_extraction(None, evaluation_id, s_id, run_id)
            except Exception as e:
                logger.error("Error running sheet extraction for %s: %s", s_id, e)

    asyncio.create_task(_run_sequential())
    mode = "In-Process Sequential Worker"

    logger.info("==================================================")
    logger.info("PIPELINE RUN INITIATED: %s", run_id)
    logger.info("Evaluation ID: %s | Subject: %s", evaluation_id, evaluation.get("subject", "N/A"))
    logger.info("Total sheets to process: %d", len(sheets))
    logger.info("Execution Dispatch: %s", mode)
    logger.info("Dedicated Run Log Folder: %s", run_dir)
    logger.info("==================================================")

    # Stream event to SSE subscribers
    await publish_event(
        evaluation_id=evaluation_id,
        event_type="pipeline_start",
        message=f"Pipeline run {run_id} initiated ({len(sheets)} sheets) via {mode}",
        data={
            "run_id": run_id,
            "total_sheets": len(sheets),
            "log_folder": run_dir,
            "subject": evaluation.get("subject", "General Assessment"),
        },
        level="info",
    )

    return PipelineStartResponse(
        success=True,
        evaluation_id=evaluation_id,
        run_id=run_id,
        log_folder=run_dir,
        total_sheets=len(sheets),
        message=f"Pipeline started for {len(sheets)} sheets via {mode}. Logs: {run_dir}",
    )


@router.post("/evaluations/{evaluation_id}/pipeline/reset")
async def reset_pipeline(evaluation_id: str):
    """
    Manually resets an evaluation and its sheets back to draft status,
    allowing a clean restart if interrupted or stuck.
    """
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    await db.evaluations.update_one(
        {"_id": ObjectId(evaluation_id)},
        {
            "$set": {
                "status": "draft",
                "pipeline_stage": "idle",
                "error": None,
            }
        },
    )

    await db.sheets.update_many(
        {"evaluation_id": evaluation_id},
        {
            "$set": {
                "status": "uploaded",
                "error": None,
                "extracted_text": None,
                "markdown_content": None,
                "evaluation": None,
                "marks": None,
                "needs_human_review": False,
            }
        },
    )

    return {
        "success": True,
        "evaluation_id": evaluation_id,
        "message": "Evaluation and sheets reset to draft state.",
    }


@router.get("/evaluations/{evaluation_id}/pipeline/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(evaluation_id: str):
    """
    Polls the progress of the 5-stage offline pipeline.
    """
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

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
    failed_sheets = [s for s in sheets if s.get("status") == "failed" or s.get("error")]
    needs_review = sum(1 for s in sheets if s.get("needs_human_review", False))

    errors = []
    for s in failed_sheets:
        name = s.get("file_name") or str(s.get("_id"))
        err = s.get("error") or "Processing failed"
        errors.append(f"{name}: {err}")

    finished = completed + len(failed_sheets)
    pct = round((finished / total) * 100) if total > 0 else 0

    return PipelineStatusResponse(
        evaluation_id=evaluation_id,
        status=evaluation.get("status", "draft"),
        pipeline_stage=evaluation.get("pipeline_stage", "idle"),
        total_sheets=total,
        completed_sheets=completed,
        failed_sheets=len(failed_sheets),
        needs_review_count=needs_review,
        progress_percentage=pct,
        errors=errors,
        latest_run_id=evaluation.get("latest_run_id"),
        latest_log_dir=evaluation.get("latest_log_dir"),
    )


# ---------------------------------------------------------------------------
# Run Log Endpoints
# ---------------------------------------------------------------------------
@router.get("/evaluations/{evaluation_id}/logs")
async def get_evaluation_logs(evaluation_id: str):
    """List all run log folders and return latest log preview for this evaluation."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    runs = list_evaluation_runs(evaluation_id)
    latest_log = ""
    latest_run_id = runs[0]["run_id"] if runs else None
    if latest_run_id:
        latest_log = read_run_log(evaluation_id, latest_run_id)

    return {
        "evaluation_id": evaluation_id,
        "total_runs": len(runs),
        "latest_run_id": latest_run_id,
        "runs": runs,
        "latest_log": latest_log,
    }


@router.get("/evaluations/{evaluation_id}/logs/{run_id}")
async def get_specific_run_log(evaluation_id: str, run_id: str):
    """Retrieve full execution log text for a specific run."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    log_content = read_run_log(evaluation_id, run_id, max_lines=2000)
    return {
        "evaluation_id": evaluation_id,
        "run_id": run_id,
        "log": log_content,
    }


# ---------------------------------------------------------------------------
# Server-Sent Events (SSE) Stream Endpoint
# ---------------------------------------------------------------------------
@router.get("/evaluations/{evaluation_id}/pipeline/stream")
async def stream_pipeline_events(evaluation_id: str, request: Request):
    """
    Server-Sent Events (SSE) stream for real-time pipeline monitoring.
    Replays recent history buffer and streams live stage updates, logs, and scores.
    """
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    queue = await subscribe_events(evaluation_id)

    async def event_generator():
        try:
            # 1. Send initial handshake
            handshake = {
                "evaluation_id": evaluation_id,
                "type": "connected",
                "level": "info",
                "message": f"Connected to live pipeline stream for evaluation {evaluation_id}",
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            }
            yield f"data: {json.dumps(handshake)}\n\n"

            # 2. Replay buffered events
            for ev in get_history(evaluation_id):
                yield f"data: {json.dumps(ev)}\n\n"

            # 3. Stream live events
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=10.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat to keep connection alive
                    yield ": ping\n\n"
        finally:
            unsubscribe_events(evaluation_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
