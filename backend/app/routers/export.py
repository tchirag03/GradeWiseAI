"""
Export API routes.
Generates real CSV and PDF exports from evaluated sheet data.
"""
import csv
import io
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.mongodb import get_database

router = APIRouter(tags=["Export"])


# ---------------------------------------------------------------------------
# POST  /evaluations/{evaluation_id}/export/csv
# ---------------------------------------------------------------------------
@router.post("/evaluations/{evaluation_id}/export/csv")
async def export_csv(evaluation_id: str, include_details: bool = False):
    """Export evaluation results as CSV."""
    db = get_database()

    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    sheets = await db.sheets.find(
        {
            "evaluation_id": evaluation_id,
            "status": "evaluation-completed",
            "evaluation_result": {"$exists": True},
        }
    ).to_list(length=None)

    if not sheets:
        raise HTTPException(
            status_code=400,
            detail="No evaluated sheets to export.",
        )

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Gather dynamic headers if include_details
    max_qs = 0
    if include_details and sheets:
        first_sheet = sheets[0]
        max_qs = len(first_sheet.get("evaluation_result", {}).get("questions", []))

    # Header row
    headers = [
        "Student Name",
        "File Name",
        "Total Score",
        "Max Score",
        "Percentage",
        "Grade",
        "Questions Evaluated",
    ]
    
    if include_details:
        for i in range(1, max_qs + 1):
            headers.extend([f"Q{i} Score", f"Q{i} Feedback"])
        headers.extend(["Overall Feedback", "Evaluation Method"])

    writer.writerow(headers)

    for sheet in sheets:
        result = sheet.get("evaluation_result", {})
        row = [
            sheet.get("student_name", "Unknown"),
            sheet.get("file_name", ""),
            result.get("total_score", 0),
            result.get("max_score", 0),
            result.get("percentage", 0),
            result.get("grade", "N/A"),
            len(result.get("questions", [])),
        ]
        
        if include_details:
            qs = result.get("questions", [])
            overall_fb = []
            eval_method = "model"
            for i in range(max_qs):
                if i < len(qs):
                    q = qs[i]
                    row.extend([q.get("total_marks", 0), q.get("feedback", "")])
                    overall_fb.append(q.get("feedback", ""))
                    if q.get("evaluation_method") == "fallback":
                        eval_method = "fallback"
                else:
                    row.extend(["", ""])
            row.extend([" | ".join(overall_fb), eval_method])
            
        writer.writerow(row)

    output.seek(0)
    eval_name = evaluation.get("name", evaluation_id)
    filename = f"{eval_name}_results.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# POST  /evaluations/{evaluation_id}/export/pdf
# ---------------------------------------------------------------------------
@router.post("/evaluations/{evaluation_id}/export/pdf")
async def export_pdf(evaluation_id: str, include_details: bool = False):
    """Export evaluation results as PDF.

    Uses reportlab if available, otherwise returns a formatted text file.
    """
    db = get_database()

    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    sheets = await db.sheets.find(
        {
            "evaluation_id": evaluation_id,
            "status": "evaluation-completed",
            "evaluation_result": {"$exists": True},
        }
    ).to_list(length=None)

    if not sheets:
        raise HTTPException(
            status_code=400,
            detail="No evaluated sheets to export.",
        )

    try:
        return _generate_pdf(evaluation, sheets, include_details)
    except ImportError:
        # reportlab not installed — fall back to plain text report
        return _generate_text_report(evaluation, sheets, include_details)


def _generate_pdf(evaluation: dict, sheets: list[dict], include_details: bool = False) -> StreamingResponse:
    """Generate a PDF report using reportlab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
    )
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    eval_name = evaluation.get("name", "Evaluation")
    elements.append(Paragraph(f"<b>{eval_name} — Results Report</b>", styles["Title"]))
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(
        f"Subject: {evaluation.get('subject', 'N/A')} | "
        f"Max Marks: {evaluation.get('max_marks', 'N/A')} | "
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 8 * mm))

    # Summary table
    data = [["Student", "Score", "Max", "%", "Grade"]]
    for s in sheets:
        r = s.get("evaluation_result", {})
        data.append([
            s.get("student_name", "Unknown"),
            str(r.get("total_score", 0)),
            str(r.get("max_score", 0)),
            f"{r.get('percentage', 0)}%",
            r.get("grade", "N/A"),
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    elements.append(table)
    
    if include_details:
        elements.append(PageBreak())
        
        for s in sheets:
            r = s.get("evaluation_result", {})
            elements.append(Paragraph(f"<b>Student: {s.get('student_name', 'Unknown')}</b>", styles["Heading2"]))
            elements.append(Spacer(1, 4 * mm))
            
            qs = r.get("questions", [])
            all_fb = []
            eval_method = "model"
            
            data = [["Component", "Awarded", "Max", "Feedback"]]
            for q in qs:
                all_fb.append(q.get("feedback", ""))
                if q.get("evaluation_method") == "fallback":
                    eval_method = "fallback"
                for c in q.get("component_scores", []):
                    data.append([
                        f"Q{q.get('question_number', '?')}: {c.get('component', '')}",
                        str(c.get('marks_awarded', 0)),
                        str(c.get('max_marks', 0)),
                        c.get("feedback", ""),
                    ])
                    
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 4 * mm))
            
            elements.append(Paragraph(f"<b>Overall Feedback:</b> {' | '.join(all_fb)}", styles["Normal"]))
            elements.append(Spacer(1, 2 * mm))
            elements.append(Paragraph(f"<b>Evaluation Method:</b> {eval_method}", styles["Normal"]))
            elements.append(Spacer(1, 8 * mm))

    doc.build(elements)
    buf.seek(0)

    eval_name_safe = eval_name.replace(" ", "_")
    filename = f"{eval_name_safe}_results.pdf"

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _generate_text_report(evaluation: dict, sheets: list[dict], include_details: bool = False) -> StreamingResponse:
    """Fallback plain-text report when reportlab is not installed."""
    lines = []
    eval_name = evaluation.get("name", "Evaluation")
    lines.append(f"{'=' * 50}")
    lines.append(f"  {eval_name} — Results Report")
    lines.append(f"  Subject: {evaluation.get('subject', 'N/A')}")
    lines.append(f"  Max Marks: {evaluation.get('max_marks', 'N/A')}")
    lines.append(f"{'=' * 50}\n")

    lines.append(f"{'Student':<25} {'Score':>6} {'Max':>6} {'%':>7} {'Grade':>6}")
    lines.append("-" * 55)

    for s in sheets:
        r = s.get("evaluation_result", {})
        lines.append(
            f"{s.get('student_name', 'Unknown'):<25} "
            f"{r.get('total_score', 0):>6.1f} "
            f"{r.get('max_score', 0):>6.1f} "
            f"{r.get('percentage', 0):>6.1f}% "
            f"{r.get('grade', 'N/A'):>6}"
        )
        
    if include_details:
        lines.append("\n\n" + "=" * 50)
        lines.append("  DETAILED RESULTS")
        lines.append("=" * 50 + "\n")
        
        for s in sheets:
            r = s.get("evaluation_result", {})
            lines.append(f"Student: {s.get('student_name', 'Unknown')}")
            lines.append("-" * 55)
            lines.append(f"{'Component':<20} {'Awarded':>8} {'Max':>8}   {'Feedback'}")
            
            qs = r.get("questions", [])
            all_fb = []
            eval_method = "model"
            for q in qs:
                all_fb.append(q.get("feedback", ""))
                if q.get("evaluation_method") == "fallback":
                    eval_method = "fallback"
                for c in q.get("component_scores", []):
                    comp_name = f"Q{q.get('question_number', '?')}: {c.get('component', '')}"
                    lines.append(
                        f"{comp_name[:19]:<20} "
                        f"{c.get('marks_awarded', 0):>8.1f} "
                        f"{c.get('max_marks', 0):>8.1f}   "
                        f"{c.get('feedback', '')}"
                    )
            lines.append("")
            lines.append(f"Overall Feedback: {' | '.join(all_fb)}")
            lines.append(f"Evaluation Method: {eval_method}")
            lines.append("\n")

    content = "\n".join(lines)
    filename = f"{eval_name.replace(' ', '_')}_results.txt"

    return StreamingResponse(
        iter([content]),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
