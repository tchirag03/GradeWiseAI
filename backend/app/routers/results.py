"""
Results and feedback API routes.
Aggregates real evaluation data from MongoDB.
"""
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.mongodb import get_database
from app.services.rubric_parser import parse_rubric_file, DEFAULT_FALLBACK_COMPONENTS

router = APIRouter(tags=["Results"])


class ResolveReviewRequest(BaseModel):
    approved: bool = True
    override_score: Optional[float] = Field(None, ge=0.0, description="Optional manual score override")
    notes: Optional[str] = Field("Reviewed and confirmed by educator.", max_length=1000)


def _calculate_grade(pct: float) -> str:
    """Standard institutional grading scale."""
    if pct >= 90:
        return "A+"
    if pct >= 80:
        return "A"
    if pct >= 70:
        return "B+"
    if pct >= 60:
        return "B"
    if pct >= 50:
        return "C"
    if pct >= 40:
        return "D"
    return "F"


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}/results  — summary
# ---------------------------------------------------------------------------
@router.get("/evaluations/{evaluation_id}/results")
async def get_results_summary(evaluation_id: str):
    """Get aggregated results for an evaluation."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Aggregate scores from evaluated sheets
    pipeline = [
        {
            "$match": {
                "evaluation_id": evaluation_id,
                "status": {"$in": ["evaluation-completed", "review-needed", "failed"]},
            }
        },
        {
            "$project": {
                "student_name": {"$ifNull": ["$student_name", "Unknown"]},
                "file_name": 1,
                "total_score": {"$ifNull": ["$evaluation_result.total_score", "$total_score", 0.0]},
                "max_score": {"$ifNull": ["$evaluation_result.max_score", "$max_score", float(evaluation.get("max_marks", 100))]},
                "percentage": {"$ifNull": ["$evaluation_result.percentage", 0.0]},
                "grade": {"$ifNull": ["$evaluation_result.grade", "F"]},
                "questions": "$evaluation_result.questions",
                "status": 1,
                "error": 1,
                "needs_human_review": 1,
                "review_reasons": 1,
            }
        },
        {"$sort": {"percentage": -1}},
    ]

    results = await db.sheets.aggregate(pipeline).to_list(length=None)

    if not results:
        return {
            "success": True,
            "evaluation_id": evaluation_id,
            "summary": {
                "total_students": 0,
                "average_score": 0,
                "highest_score": 0,
                "lowest_score": 0,
                "average_percentage": 0,
            },
            "results": [],
        }

    scores = [r["total_score"] for r in results]
    percentages = [r["percentage"] for r in results]

    # Stringify _id for JSON serialisation and compute fields
    for r in results:
        r["_id"] = str(r["_id"])

        qs = r.get("questions") or []
        top_loss_component = None
        max_loss = -1.0
        feedback_summary = ""
        eval_method = "model"

        for q in qs:
            if not feedback_summary and q.get("feedback"):
                feedback_summary = q["feedback"][:120]
            if q.get("evaluation_method") == "fallback":
                eval_method = "fallback"

            for comp in q.get("component_scores", []):
                loss = comp.get("max_marks", 0) - comp.get("marks_awarded", 0)
                if loss > max_loss:
                    max_loss = loss
                    top_loss_component = f"{comp.get('component', 'Unknown')} (-{loss})"

        r["top_loss_component"] = top_loss_component
        r["feedback_summary"] = feedback_summary
        r["evaluation_method"] = eval_method

        r.pop("questions", None)

    return {
        "success": True,
        "evaluation_id": evaluation_id,
        "summary": {
            "total_students": len(results),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
            "highest_score": round(max(scores), 1) if scores else 0.0,
            "lowest_score": round(min(scores), 1) if scores else 0.0,
            "average_percentage": round(sum(percentages) / len(percentages), 1) if percentages else 0.0,
        },
        "results": results,
    }


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}/results/{sheet_id}  — detailed
# ---------------------------------------------------------------------------
@router.get("/evaluations/{evaluation_id}/results/{sheet_id}")
async def get_detailed_result(evaluation_id: str, sheet_id: str):
    """Get detailed per-question breakdown for a sheet."""
    if not ObjectId.is_valid(evaluation_id) or not ObjectId.is_valid(sheet_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    db = get_database()
    doc = await db.sheets.find_one(
        {"_id": ObjectId(sheet_id), "evaluation_id": evaluation_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Sheet not found")

    eval_result = doc.get("evaluation_result")
    if not eval_result:
        return {
            "success": True,
            "sheet_id": sheet_id,
            "status": doc.get("status", "pending"),
            "message": "Evaluation not yet completed for this sheet.",
        }

    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})

    # 1. Fetch rubric attached to this evaluation (by evaluation_id or rubric_id)
    rubric_doc = await db.rubrics.find_one({"evaluation_id": evaluation_id})
    if not rubric_doc and evaluation and evaluation.get("rubric_id"):
        try:
            rubric_doc = await db.rubrics.find_one({"_id": ObjectId(evaluation.get("rubric_id"))})
        except Exception:
            pass

    rubric_file_name = rubric_doc.get("file_name") if rubric_doc else None
    rubric_components = []

    # 2. Extract components from rubric doc or parse attached rubric file
    if rubric_doc and rubric_doc.get("components"):
        rubric_components = rubric_doc["components"]
    elif rubric_doc and rubric_doc.get("file_path"):
        rubric_components = parse_rubric_file(rubric_doc["file_path"])
        if rubric_components:
            # Cache parsed components in MongoDB
            await db.rubrics.update_one(
                {"_id": rubric_doc["_id"]},
                {"$set": {"components": rubric_components}}
            )

    # 3. Fallback: extract evaluated components from sheet's evaluation_result
    if not rubric_components and eval_result:
        seen = set()
        for q in eval_result.get("questions", []):
            for comp in q.get("component_scores", []):
                c_name = comp.get("component")
                if c_name and c_name not in seen:
                    seen.add(c_name)
                    rubric_components.append({
                        "name": c_name,
                        "marks": comp.get("max_marks", 0),
                        "model_answer": comp.get("model_answer") or comp.get("feedback", ""),
                    })

    # 4. Fallback to default rubric components if none available
    if not rubric_components:
        rubric_components = DEFAULT_FALLBACK_COMPONENTS

    # Ensure model answers on question component_scores match rubric components if blank
    comp_map = {c["name"].lower(): c.get("model_answer", "") for c in rubric_components}
    for q in eval_result.get("questions", []):
        for comp in q.get("component_scores", []):
            if not comp.get("model_answer"):
                c_name = comp.get("component", "").lower()
                for k, v in comp_map.items():
                    if k in c_name or c_name in k:
                        comp["model_answer"] = v
                        break

    pct = eval_result.get("percentage", 0)
    boundaries_list = [
        {"grade": "D", "min_percentage": 40},
        {"grade": "C", "min_percentage": 50},
        {"grade": "B", "min_percentage": 60},
        {"grade": "B+", "min_percentage": 70},
        {"grade": "A", "min_percentage": 80},
        {"grade": "A+", "min_percentage": 90},
    ]
    boundaries_dict = {b["grade"]: b["min_percentage"] for b in boundaries_list}
    closest_grade = None
    min_diff = float("inf")
    for g, b in boundaries_dict.items():
        diff = abs(pct - b)
        if diff < min_diff:
            min_diff = diff
            closest_grade = g

    return {
        "success": True,
        "sheet_id": sheet_id,
        "student": {
            "name": doc.get("student_name", "Unknown"),
            "file_name": doc.get("file_name", ""),
        },
        "needs_human_review": doc.get("needs_human_review", False),
        "review_reasons": doc.get("review_reasons", []),
        "diagram_description": doc.get("diagram_descriptions", ""),
        "evaluation": eval_result,
        "crops": doc.get("crops", []),
        "status": doc.get("status", "unknown"),
        "error": doc.get("error"),
        "rubric_file_name": rubric_file_name,
        "rubric_components": rubric_components,
        "grade_boundaries": boundaries_list,
        "grade_boundary_details": {
            "boundaries": boundaries_dict,
            "closest": closest_grade,
        },
    }


# ---------------------------------------------------------------------------
# Stage 4: Review Queue Endpoints
# ---------------------------------------------------------------------------
@router.get("/evaluations/{evaluation_id}/review_queue")
async def get_review_queue(evaluation_id: str):
    """Get all sheets flagged for human review."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    cursor = db.sheets.find({
        "evaluation_id": evaluation_id,
        "needs_human_review": True,
    })

    flagged_sheets = []
    async for doc in cursor:
        flagged_sheets.append({
            "sheet_id": str(doc["_id"]),
            "file_name": doc.get("file_name"),
            "student_name": doc.get("student_name", "Unknown"),
            "review_reasons": doc.get("review_reasons", []),
            "total_score": doc.get("evaluation_result", {}).get("total_score", doc.get("total_score")),
            "percentage": doc.get("evaluation_result", {}).get("percentage"),
            "grade": doc.get("evaluation_result", {}).get("grade"),
            "evaluation_result": doc.get("evaluation_result"),
        })

    return {
        "success": True,
        "evaluation_id": evaluation_id,
        "count": len(flagged_sheets),
        "sheets": flagged_sheets,
    }


@router.post("/evaluations/{evaluation_id}/review_queue/{sheet_id}/resolve")
async def resolve_review(evaluation_id: str, sheet_id: str, payload: ResolveReviewRequest):
    """
    Allows a human evaluator to override or approve a flagged grading.
    payload: {"approved": bool, "override_score": Optional[float], "notes": str}
    """
    if not ObjectId.is_valid(evaluation_id) or not ObjectId.is_valid(sheet_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    db = get_database()
    sheet = await db.sheets.find_one({"_id": ObjectId(sheet_id), "evaluation_id": evaluation_id})
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found")

    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})

    update_fields = {
        "needs_human_review": False,
        "status": "evaluation-completed",
        "human_review_notes": payload.notes or "Reviewed and confirmed by educator.",
    }

    if payload.override_score is not None:
        eval_res = sheet.get("evaluation_result") or {}
        max_s = float(
            eval_res.get("max_score")
            or sheet.get("max_score")
            or (evaluation.get("max_marks", 100) if evaluation else 100)
        )
        if max_s <= 0:
            max_s = 100.0

        override_val = min(float(payload.override_score), max_s)
        pct = round((override_val / max_s * 100), 1) if max_s > 0 else 0.0

        eval_res["total_score"] = override_val
        eval_res["max_score"] = max_s
        eval_res["percentage"] = pct
        eval_res["grade"] = _calculate_grade(pct)

        update_fields["total_score"] = override_val
        update_fields["max_score"] = max_s
        update_fields["evaluation_result"] = eval_res

    await db.sheets.update_one({"_id": ObjectId(sheet_id)}, {"$set": update_fields})

    return {"success": True, "message": f"Sheet {sheet_id} human review resolved."}
