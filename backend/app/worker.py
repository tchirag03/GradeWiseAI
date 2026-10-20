"""
Arq background worker definition.
Orchestrates the offline evaluation pipeline powered by Unified Qwen3-VL (8B):
  Stage 0: Ingestion & Resolution Normalization
  Stage 1: Unified Multimodal Transcription (Text, Math, Diagrams)
  Stage 2: Rubric & Structural Alignment
  Stage 3: Automated Scoring & Grading
  Stage 4: Flagging & Educator Triage Queue
"""
import asyncio
from datetime import datetime, timezone
from bson import ObjectId

from app.core.config import settings
from app.core.mongodb import get_database, connect_db, close_db
from app.services.stage0_preprocess import get_preprocessing_service
from app.services.stage1_transcribe import get_transcription_service
from app.services.stage2_describe import get_diagram_service
from app.services.stage3_grade import get_grading_service
from app.services.structuring_service import get_structuring_service
from app.services.unified_vlm_service import get_unified_vlm_service


# ---------------------------------------------------------------------------
# Task 1: Per-Sheet Unified VLM Evaluation
# ---------------------------------------------------------------------------
async def process_sheet_extraction(ctx, evaluation_id: str, sheet_id: str):
    """
    Performs unified multimodal perception & rubric grading using Qwen3-VL:8b.
    """
    db = get_database()
    sheet = await db.sheets.find_one({"_id": ObjectId(sheet_id)})
    if not sheet:
        print(f"[Worker] Sheet {sheet_id} not found.")
        return

    try:
        await db.sheets.update_one(
            {"_id": ObjectId(sheet_id)},
            {"$set": {"status": "transcribing-processing"}}
        )

        vlm_svc = get_unified_vlm_service()
        await vlm_svc.evaluate_sheet(evaluation_id, sheet_id)
        print(f"[Worker] Unified VLM evaluation completed for sheet {sheet_id}.")

        # Check if all sheets for this evaluation have completed
        pending_count = await db.sheets.count_documents({
            "evaluation_id": evaluation_id,
            "status": {"$in": ["uploaded", "preprocessing-pending", "preprocessing-processing", "transcribing-processing", "grading-processing"]}
        })

        if pending_count == 0:
            print(f"[Worker] All sheets processed for evaluation {evaluation_id}. Updating evaluation status to completed.")
            await db.evaluations.update_one(
                {"_id": ObjectId(evaluation_id)},
                {"$set": {"status": "completed", "pipeline_stage": "completed"}}
            )

    except Exception as exc:
        print(f"[Worker] Error in sheet extraction {sheet_id}: {exc}")
        await db.sheets.update_one(
            {"_id": ObjectId(sheet_id)},
            {
                "$set": {
                    "status": "review-needed",
                    "error": str(exc),
                    "needs_human_review": True,
                    "review_reasons": ["vlm_evaluation_error"],
                }
            }
        )


# ---------------------------------------------------------------------------
# Task 2: Evaluation-Level Batch Grading (Stage 3 & Stage 4)
# ---------------------------------------------------------------------------
async def process_evaluation_batch_grading(ctx, evaluation_id: str):
    """
    Stage 3: Groups by question across ALL sheets in this evaluation to reuse KV-cache.
    Stage 4: Evaluates boundary scores and flags scripts for human review.
    """
    db = get_database()
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        return

    sheets = await db.sheets.find({
        "evaluation_id": evaluation_id,
        "status": "grading-pending",
    }).to_list(length=None)

    if not sheets:
        return

    print(f"[Worker] Starting Stage 3 batch grading for {len(sheets)} sheets across questions.")

    # Mark sheets as processing
    await db.sheets.update_many(
        {"_id": {"$in": [s["_id"] for s in sheets]}},
        {"$set": {"status": "grading-processing"}}
    )

    # Fetch rubric
    rubric_id = evaluation.get("rubric_id")
    rubric_components = []
    if rubric_id:
        rubric_doc = await db.rubrics.find_one({"_id": ObjectId(rubric_id)})
        if rubric_doc and rubric_doc.get("components"):
            rubric_components = rubric_doc["components"]

    if not rubric_components:
        rubric_components = [
            {"name": "Correctness", "marks": 5, "model_answer": "Standard correct steps.", "mark_bands": "5: full, 2-3: partial, 0: wrong"},
            {"name": "Clarity & Diagrams", "marks": 5, "model_answer": "Clear tree/graph structure.", "mark_bands": "5: complete tree, 0: missing"},
        ]

    max_marks = float(evaluation.get("max_marks", 100))
    grader = get_grading_service()

    # Organize questions across all sheets
    # We map: question_number -> list of submissions
    submissions_per_q: dict[int, list[dict]] = {}
    for sheet in sheets:
        s_id = str(sheet["_id"])
        structured = sheet.get("structured_data", {})
        questions = structured.get("questions", [])
        diagram_desc = sheet.get("diagram_descriptions", "")

        for q in questions:
            q_num = q.get("question_number", 1)
            if q_num not in submissions_per_q:
                submissions_per_q[q_num] = []
            submissions_per_q[q_num].append({
                "sheet_id": s_id,
                "question_text": q.get("question_text", f"Question {q_num}"),
                "answer_text": q.get("answer", {}).get("raw_text", ""),
                "diagram_desc": diagram_desc,
            })

    # Initialize score records for each sheet
    sheet_scores: dict[str, list[dict]] = {str(s["_id"]): [] for s in sheets}

    # BATCH BY QUESTION: The prompt prefix is prefilled ONCE and KV cache reused!
    for q_num, subs in sorted(submissions_per_q.items()):
        q_text = subs[0]["question_text"]
        # Match with a rubric component if available
        comp_idx = (q_num - 1) % len(rubric_components)
        comp = rubric_components[comp_idx]

        marks_for_q = comp.get("marks", 10.0)
        model_ans = comp.get("model_answer", "")
        mark_bands = comp.get("mark_bands", "")

        print(f"[Worker] Grading Q{q_num} for {len(subs)} students (reusing KV cache prefix)...")

        # Run batch question grading
        batch_results = await asyncio.to_thread(
            grader.batch_grade_question_across_sheets,
            q_text,
            comp.get("name", f"Question {q_num}"),
            marks_for_q,
            model_ans,
            mark_bands,
            subs,
        )

        for res in batch_results:
            s_id = res["sheet_id"]
            score_data = res["score"]
            sheet_scores[s_id].append({
                "question_number": q_num,
                "question_text": q_text,
                "marks_awarded": score_data["marks_awarded"],
                "max_marks": marks_for_q,
                "feedback": score_data["feedback"],
                "flagged": score_data.get("flagged_for_review", False),
            })

    # Stage 4: Aggregate scores and trigger human review flags
    for sheet in sheets:
        s_id = str(sheet["_id"])
        scores = sheet_scores.get(s_id, [])
        total_score = sum(q["marks_awarded"] for q in scores)
        q_max_total = sum(q["max_marks"] for q in scores)
        normalized_total = (total_score / q_max_total * max_marks) if q_max_total > 0 else 0
        percentage = round((normalized_total / max_marks * 100), 1) if max_marks > 0 else 0
        letter_grade = grader.calculate_grade(percentage)

        eval_result = {
            "questions": scores,
            "total_score": round(normalized_total, 1),
            "max_score": max_marks,
            "percentage": percentage,
            "grade": letter_grade,
        }

        # Stage 4 Flagging Rules:
        review_reasons = []
        needs_review = False

        # Rule A: Score is within 2.5% of grade boundary
        boundary_dist = min(abs(percentage - cutoff) for cutoff in [90, 80, 70, 60, 50, 40])
        if boundary_dist <= 2.5:
            needs_review = True
            review_reasons.append(f"Borderline score ({percentage}%, within 2.5% of grade threshold)")

        # Rule B: Unclear markers in transcription or diagrams
        if sheet.get("unclear_count", 0) > 2 or sheet.get("has_unclear_diagram", False):
            needs_review = True
            review_reasons.append("Unclear handwriting or illegible diagram markers")

        # Rule C: Any question flagged during generation
        if any(q.get("flagged") for q in scores):
            needs_review = True
            review_reasons.append("Grammar parsing failed during grading")

        final_status = "review-needed" if needs_review else "evaluation-completed"

        await db.sheets.update_one(
            {"_id": ObjectId(s_id)},
            {
                "$set": {
                    "status": final_status,
                    "evaluation_result": eval_result,
                    "needs_human_review": needs_review,
                    "review_reasons": review_reasons,
                    "evaluation_completed_at": datetime.now(timezone.utc).isoformat(),
                }
            }
        )

    await db.evaluations.update_one(
        {"_id": ObjectId(evaluation_id)},
        {"$set": {"status": "completed", "pipeline_stage": "completed"}}
    )
    print(f"[Worker] Batch grading finished for evaluation {evaluation_id}.")


# ---------------------------------------------------------------------------
# Arq Worker Settings
# ---------------------------------------------------------------------------
class WorkerSettings:
    functions = [process_sheet_extraction, process_evaluation_batch_grading]
    on_startup = connect_db
    on_shutdown = close_db
    max_jobs = 2  # Concurrency limit to prevent CPU core saturation
