"""
Arq background worker definition.
Orchestrates the offline evaluation pipeline powered by Unified Qwen3-VL (8B):
  Stage 0: Ingestion & Resolution Normalization
  Stage 1: Unified Multimodal Transcription (Text, Math, Diagrams)
  Stage 2: Rubric & Structural Alignment
  Stage 3: Automated Scoring & Grading
  Stage 4: Flagging & Educator Triage Queue
Stores full execution logs in a dedicated folder for each run:
  logs/{evaluation_id}/{run_id}/run.log
  logs/{evaluation_id}/{run_id}/summary.json
"""
import asyncio
from datetime import datetime, timezone
from bson import ObjectId

from app.core.config import settings
from app.core.mongodb import get_database, connect_db, close_db
from app.core.redis_client import connect_redis, close_redis
from app.services.unified_vlm_service import get_unified_vlm_service
from app.core.logging_config import get_run_logger, write_run_summary
from app.core.event_bus import publish_event


# ---------------------------------------------------------------------------
# Task 1: Per-Sheet Unified VLM Evaluation
# ---------------------------------------------------------------------------
async def process_sheet_extraction(ctx, evaluation_id: str, sheet_id: str, run_id: str | None = None):
    """
    Performs unified multimodal perception & rubric grading using Qwen3-VL:8b.
    Streams execution logs into the dedicated run directory and publishes live SSE events.
    """
    if not ObjectId.is_valid(evaluation_id) or not ObjectId.is_valid(sheet_id):
        return

    db = get_database()
    sheet = await db.sheets.find_one({"_id": ObjectId(sheet_id)})
    if not sheet:
        return

    # Resolve run_id from evaluation document if not explicitly passed
    if not run_id:
        eval_doc = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
        run_id = eval_doc.get("latest_run_id") if eval_doc else None

    logger = get_run_logger(evaluation_id, run_id)
    file_name = sheet.get("file_name", "unknown")
    page_count = sheet.get("page_count", len(sheet.get("pages", [])) or 1)
    page_info = f" ({page_count} pages)" if page_count > 1 else ""
    logger.info(">>> Processing sheet %s [File: %s%s]...", sheet_id, file_name, page_info)

    await publish_event(
        evaluation_id=evaluation_id,
        event_type="sheet_start",
        message=f"Starting perception & evaluation for '{file_name}'{page_info}...",
        data={"sheet_id": sheet_id, "file_name": file_name, "page_count": page_count},
        level="info",
    )

    try:
        await db.sheets.update_one(
            {"_id": ObjectId(sheet_id)},
            {"$set": {"status": "transcribing-processing"}}
        )

        vlm_svc = get_unified_vlm_service()
        result = await vlm_svc.evaluate_sheet(evaluation_id, sheet_id, logger=logger)

        total_score = result.get("total_score", 0.0)
        max_score = result.get("max_score", 0.0)
        grade = result.get("evaluation_result", {}).get("grade", "N/A")
        needs_review = result.get("needs_human_review", False)

        logger.info(
            "✓ Sheet %s evaluated successfully! Score: %.1f / %.1f | Needs Review: %s",
            sheet_id,
            total_score,
            max_score,
            needs_review,
        )

        await publish_event(
            evaluation_id=evaluation_id,
            event_type="sheet_completed",
            message=f"✓ Graded '{file_name}'{page_info}: {total_score:.1f}/{max_score} (Grade: {grade})" + (" [Needs Human Review]" if needs_review else ""),
            data={
                "sheet_id": sheet_id,
                "file_name": file_name,
                "student_name": result.get("student_name"),
                "score": total_score,
                "max_score": max_score,
                "grade": grade,
                "needs_review": needs_review,
                "page_count": page_count,
            },
            level="warning" if needs_review else "success",
        )

    except Exception as exc:
        import traceback
        err_msg = str(exc)
        if not err_msg:
            err_msg = f"{type(exc).__name__}: Model inference request timed out or was interrupted."
        logger.error("Sheet %s FAILED: %s", sheet_id, err_msg)
        logger.error("Full traceback:\n%s", traceback.format_exc())
        await db.sheets.update_one(
            {"_id": ObjectId(sheet_id)},
            {
                "$set": {
                    "status": "failed",
                    "error": err_msg,
                    "needs_human_review": True,
                    "review_reasons": [f"Evaluation error: {err_msg}"],
                    "evaluation_completed_at": datetime.now(timezone.utc).isoformat(),
                }
            }
        )

        await publish_event(
            evaluation_id=evaluation_id,
            event_type="sheet_error",
            message=f"✗ Error processing '{file_name}': {err_msg}",
            data={"sheet_id": sheet_id, "file_name": file_name, "error": err_msg},
            level="error",
        )

    finally:
        # Check if all sheets for this evaluation have finished
        pending_count = await db.sheets.count_documents({
            "evaluation_id": evaluation_id,
            "status": {
                "$in": [
                    "uploaded",
                    "preprocessing-pending",
                    "preprocessing-processing",
                    "transcribing-processing",
                    "grading-processing",
                ]
            },
        })

        if pending_count == 0:
            # Atomic lock to prevent duplicate finalization from concurrent sheet tasks
            lock_res = await db.evaluations.update_one(
                {
                    "_id": ObjectId(evaluation_id),
                    "pipeline_stage": {"$ne": "completed"},
                },
                {"$set": {"pipeline_stage": "finalizing"}},
            )
            if lock_res.modified_count == 0:
                return

            total_sheets = await db.sheets.count_documents({"evaluation_id": evaluation_id})
            failed_sheets = await db.sheets.count_documents({"evaluation_id": evaluation_id, "status": "failed"})
            completed_sheets = await db.sheets.count_documents({
                "evaluation_id": evaluation_id,
                "status": {"$in": ["evaluation-completed", "review-needed"]},
            })
            review_needed = await db.sheets.count_documents({"evaluation_id": evaluation_id, "needs_human_review": True})

            final_status = "failed" if (failed_sheets == total_sheets and total_sheets > 0) else "completed"
            logger.info("==================================================")
            logger.info("PIPELINE RUN COMPLETE for Evaluation %s", evaluation_id)
            logger.info(
                "Final Status: %s | Total: %d | Completed: %d | Failed: %d | Needs Review: %d",
                final_status,
                total_sheets,
                completed_sheets,
                failed_sheets,
                review_needed,
            )
            logger.info("Run folder: %s", getattr(logger, "run_dir", ""))
            logger.info("==================================================")

            # Record machine-readable run summary
            run_dir = getattr(logger, "run_dir", None)
            log_file = getattr(logger, "log_file", None)
            run_id_val = getattr(logger, "run_id", run_id or "run_latest")

            if run_dir:
                summary = {
                    "evaluation_id": evaluation_id,
                    "run_id": run_id_val,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "final_status": final_status,
                    "total_sheets": total_sheets,
                    "completed_sheets": completed_sheets,
                    "failed_sheets": failed_sheets,
                    "review_needed": review_needed,
                    "run_directory": run_dir,
                    "log_file": log_file,
                }
                write_run_summary(run_dir, summary)

            await db.evaluations.update_one(
                {"_id": ObjectId(evaluation_id)},
                {
                    "$set": {
                        "status": final_status,
                        "pipeline_stage": "completed",
                        "latest_log_dir": run_dir,
                        "latest_log_file": log_file,
                    }
                },
            )

            await publish_event(
                evaluation_id=evaluation_id,
                event_type="pipeline_done",
                message=f"Pipeline finished! Completed: {completed_sheets}/{total_sheets}, Failed: {failed_sheets}, Needs Review: {review_needed}",
                data={
                    "final_status": final_status,
                    "completed": completed_sheets,
                    "failed": failed_sheets,
                    "review_needed": review_needed,
                    "total": total_sheets,
                    "log_folder": run_dir,
                },
                level="error" if final_status == "failed" else "success",
            )


# ---------------------------------------------------------------------------
# Arq Worker Settings
# ---------------------------------------------------------------------------
async def worker_startup(ctx):
    await connect_db()
    await connect_redis()


async def worker_shutdown(ctx):
    await close_redis()
    await close_db()


class WorkerSettings:
    functions = [process_sheet_extraction]
    on_startup = worker_startup
    on_shutdown = worker_shutdown
