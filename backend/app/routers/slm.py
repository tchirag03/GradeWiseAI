"""
SLM evaluation API routes.
Evaluates structured Q&A answers against a rubric using Qwen2.5-0.5B-Instruct.
"""
import asyncio
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.mongodb import get_database
from app.services.slm_service import get_slm_service, SLMService
from app.schemas.slm import (
    SLMStartResponse,
    SLMStatusResponse,
    SLMProgress,
    SLMResultResponse,
    SLMEvaluationResult,
    QuestionScore,
    ComponentScore,
)

router = APIRouter(tags=["Evaluation"])


# ---------------------------------------------------------------------------
# Default rubric (used when no custom rubric is attached to the evaluation)
# ---------------------------------------------------------------------------
_DEFAULT_RUBRIC = [
    {"name": "Correctness", "marks": 5},
    {"name": "Completeness", "marks": 3},
    {"name": "Clarity", "marks": 2},
]


# ---------------------------------------------------------------------------
# POST  /evaluations/{evaluation_id}/evaluation/start
# ---------------------------------------------------------------------------
@router.post(
    "/evaluations/{evaluation_id}/evaluation/start",
    response_model=SLMStartResponse,
)
async def start_evaluation(evaluation_id: str):
    """Start SLM-based evaluation for all structuring-completed sheets.

    Processing happens in the background; frontend polls /evaluation/status.
    """
    db = get_database()

    # Validate evaluation
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Gather sheets that have structured data but haven't been evaluated yet
    sheets = await db.sheets.find(
        {
            "evaluation_id": evaluation_id,
            "status": {"$in": ["structuring-completed", "evaluation-failed"]},
        }
    ).to_list(length=None)

    if not sheets:
        raise HTTPException(
            status_code=400,
            detail="No sheets ready for evaluation. Run structuring first.",
        )

    job_id = str(uuid.uuid4())
    total = len(sheets)

    # Fetch rubric (use default if none attached)
    rubric_id = evaluation.get("rubric_id")
    rubric_components = _DEFAULT_RUBRIC
    if rubric_id:
        rubric_doc = await db.rubrics.find_one({"_id": ObjectId(rubric_id)})
        if rubric_doc and rubric_doc.get("components"):
            rubric_components = rubric_doc["components"]

    max_marks = evaluation.get("max_marks", 100)

    # Mark sheets as pending
    sheet_ids = [s["_id"] for s in sheets]
    await db.sheets.update_many(
        {"_id": {"$in": sheet_ids}},
        {
            "$set": {
                "status": "evaluation-pending",
                "evaluation_job_id": job_id,
            }
        },
    )

    # Create job record
    await db.slm_jobs.insert_one(
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
    asyncio.create_task(
        _process_evaluation_batch(
            job_id, evaluation_id, sheets, rubric_components, max_marks,
        )
    )

    return SLMStartResponse(
        success=True,
        job_id=job_id,
        message=f"SLM evaluation started for {total} sheet(s)",
        total_sheets=total,
    )


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------
async def _process_evaluation_batch(
    job_id: str,
    evaluation_id: str,
    sheets: list[dict],
    rubric_components: list[dict],
    max_marks: float,
) -> None:
    """Evaluate each sheet's structured questions through the SLM."""
    db = get_database()
    slm = get_slm_service()
    completed = 0
    failed = 0

    for sheet in sheets:
        sheet_id = sheet["_id"]
        structured = sheet.get("structured_data", {})

        try:
            await db.sheets.update_one(
                {"_id": sheet_id},
                {"$set": {"status": "evaluation-processing"}},
            )

            questions = structured.get("questions", [])
            num_questions = max(len(questions), 1)

            # Distribute marks evenly across questions
            marks_per_q = max_marks / num_questions
            per_q_rubric = [
                {"name": c["name"], "marks": round(c["marks"] * marks_per_q / 10, 1)}
                for c in rubric_components
            ]

            question_scores = []
            total_score = 0.0

            for q in questions:
                q_text = q.get("question_text", "")
                a_text = q.get("answer", {}).get("raw_text", "")

                model_answers = [c.get("model_answer", "") for c in rubric_components]

                # Run LLM evaluation in a thread (CPU-bound)
                result = await asyncio.to_thread(
                    slm.evaluate_answer,
                    q_text, a_text, per_q_rubric, marks_per_q, model_answers
                )

                q_total = result["total_marks"]
                total_score += q_total
                
                q_pct = round(q_total / marks_per_q * 100, 1) if marks_per_q > 0 else 0
                boundaries = [(90, "A+"), (80, "A"), (70, "B+"), (60, "B"), (50, "C"), (40, "D")]
                next_boundary_marks = None
                next_grade = None
                for b_pct, b_grade in reversed(boundaries):
                    if q_pct < b_pct:
                        next_boundary_marks = b_pct * marks_per_q / 100
                        next_grade = b_grade
                        break
                
                if next_grade:
                    marks_needed = round(next_boundary_marks - q_total, 1)
                    grade_context = f"{q_pct}% — {marks_needed} marks from {next_grade}"
                else:
                    grade_context = f"{q_pct}% — Top Grade"

                question_scores.append({
                    "question_number": q.get("question_number", 0),
                    "question_text": q_text,
                    "component_scores": result["components"],
                    "total_marks": q_total,
                    "max_marks": marks_per_q,
                    "feedback": result["feedback"],
                    "grade_context": grade_context,
                    "evaluation_method": result.get("evaluation_method", "model"),
                })

            percentage = round(total_score / max_marks * 100, 1) if max_marks > 0 else 0
            grade = SLMService.calculate_grade(percentage)

            evaluation_result = {
                "questions": question_scores,
                "total_score": round(total_score, 1),
                "max_score": max_marks,
                "percentage": percentage,
                "grade": grade,
            }

            await db.sheets.update_one(
                {"_id": sheet_id},
                {
                    "$set": {
                        "status": "evaluation-completed",
                        "evaluation_result": evaluation_result,
                        "evaluation_completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
            completed += 1

        except Exception as exc:
            await db.sheets.update_one(
                {"_id": sheet_id},
                {
                    "$set": {
                        "status": "evaluation-failed",
                        "evaluation_error": str(exc),
                    }
                },
            )
            failed += 1

        # Update job progress
        await db.slm_jobs.update_one(
            {"_id": job_id},
            {"$set": {"completed": completed, "failed": failed}},
        )

    # Finalise job
    final_status = "completed" if failed == 0 else "failed"
    await db.slm_jobs.update_one(
        {"_id": job_id},
        {
            "$set": {
                "status": final_status,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}/evaluation/status
# ---------------------------------------------------------------------------
@router.get(
    "/evaluations/{evaluation_id}/evaluation/status",
    response_model=SLMStatusResponse,
)
async def get_evaluation_status(evaluation_id: str):
    """Get the latest SLM evaluation job status."""
    db = get_database()

    job = await db.slm_jobs.find_one(
        {"evaluation_id": evaluation_id},
        sort=[("started_at", -1)],
    )

    if not job:
        return SLMStatusResponse(
            status="pending",
            progress=SLMProgress(total=0, completed=0, failed=0, percentage=0),
        )

    total = job["total"]
    completed_count = job["completed"]
    failed_count = job["failed"]
    pct = round((completed_count + failed_count) / total * 100) if total > 0 else 0

    return SLMStatusResponse(
        status=job["status"],
        progress=SLMProgress(
            total=total,
            completed=completed_count,
            failed=failed_count,
            percentage=pct,
        ),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
    )


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}/evaluation/result/{sheet_id}
# ---------------------------------------------------------------------------
@router.get(
    "/evaluations/{evaluation_id}/evaluation/result/{sheet_id}",
    response_model=SLMResultResponse,
)
async def get_evaluation_result(evaluation_id: str, sheet_id: str):
    """Get SLM evaluation result for a specific sheet."""
    db = get_database()

    doc = await db.sheets.find_one(
        {"_id": ObjectId(sheet_id), "evaluation_id": evaluation_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Sheet not found")

    status = doc.get("status", "uploaded")

    if status == "evaluation-completed":
        data = doc.get("evaluation_result", {})
        return SLMResultResponse(
            sheet_id=sheet_id,
            status="completed",
            result=SLMEvaluationResult(
                questions=[
                    QuestionScore(
                        question_number=q["question_number"],
                        question_text=q["question_text"],
                        component_scores=[
                            ComponentScore(**c) for c in q.get("component_scores", [])
                        ],
                        total_marks=q.get("total_marks", 0),
                        max_marks=q.get("max_marks", 0),
                        feedback=q.get("feedback", ""),
                        grade_context=q.get("grade_context", ""),
                        evaluation_method=q.get("evaluation_method", "model"),
                    )
                    for q in data.get("questions", [])
                ],
                total_score=data.get("total_score", 0),
                max_score=data.get("max_score", 0),
                percentage=data.get("percentage", 0),
                grade=data.get("grade", "N/A"),
            ),
        )
    elif status == "evaluation-failed":
        return SLMResultResponse(
            sheet_id=sheet_id,
            status="failed",
            error=doc.get("evaluation_error", "Unknown error"),
        )
    elif status in ("evaluation-pending", "evaluation-processing"):
        return SLMResultResponse(sheet_id=sheet_id, status="running")
    else:
        return SLMResultResponse(sheet_id=sheet_id, status="pending")
