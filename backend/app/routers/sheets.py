"""
Answer sheet management API routes.
Handles real file uploads, local disk storage, and MongoDB metadata.
"""
import os
import re
import shutil
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.core.mongodb import get_database
from app.schemas.sheet import (
    DeleteSheetResponse,
    ListSheetsResponse,
    SheetMetadata,
    UploadedSheetInfo,
    UploadSheetsResponse,
)
from app.services.rubric_parser import parse_rubric_file

router = APIRouter(tags=["Sheets"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
ALLOWED_RUBRIC_EXTENSIONS = {".pdf", ".txt", ".docx", ".doc"}


def _sanitize_filename(filename: str | None, default_name: str = "upload.bin") -> str:
    """Sanitize uploaded filename to prevent directory traversal and invalid chars."""
    if not filename:
        return default_name
    clean_name = os.path.basename(filename)
    clean_name = re.sub(r"[\x00/\\:]", "", clean_name).strip()
    clean_name = re.sub(r"[^\w\s\.-]", "_", clean_name)
    if not clean_name or clean_name.startswith("."):
        clean_name = f"file_{uuid.uuid4().hex[:6]}_{clean_name}"
    return clean_name


def _validate_extension(filename: str) -> None:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )


def _validate_rubric_extension(filename: str) -> None:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_RUBRIC_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported rubric file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_RUBRIC_EXTENSIONS))}",
        )


def _is_safe_path(base_dir: str, target_path: str) -> bool:
    """Ensure target path doesn't escape base_dir."""
    try:
        abs_base = os.path.abspath(base_dir)
        abs_target = os.path.abspath(target_path)
        return os.path.commonpath([abs_base]) == os.path.commonpath([abs_base, abs_target])
    except Exception:
        return False


def _ensure_upload_dir(evaluation_id: str) -> str:
    """Create and return the upload directory for an evaluation."""
    upload_path = os.path.join(settings.upload_dir, evaluation_id)
    os.makedirs(upload_path, exist_ok=True)
    return upload_path


# ---------------------------------------------------------------------------
# POST  /evaluations/{evaluation_id}/sheets  —  upload answer sheets (bulk)
# ---------------------------------------------------------------------------
@router.post(
    "/evaluations/{evaluation_id}/sheets",
    response_model=UploadSheetsResponse,
)
async def upload_sheets(
    evaluation_id: str,
    files: list[UploadFile] = File(..., description="One or more answer sheet images/PDFs"),
):
    """Upload answer sheets for a given evaluation.

    • Saves each file to  uploads/<evaluation_id>/
    • Inserts a metadata document into the MongoDB `sheets` collection
    """
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    upload_dir = _ensure_upload_dir(evaluation_id)
    uploaded: list[UploadedSheetInfo] = []

    for file in files:
        safe_filename = _sanitize_filename(file.filename, f"sheet_{uuid.uuid4().hex[:6]}.png")
        _validate_extension(safe_filename)

        # Unique file destination if already exists
        dest_path = os.path.join(upload_dir, safe_filename)
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(safe_filename)
            safe_filename = f"{base}_{uuid.uuid4().hex[:6]}{ext}"
            dest_path = os.path.join(upload_dir, safe_filename)

        # Persist to disk
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        file_size = os.path.getsize(dest_path)

        # Insert metadata into MongoDB
        doc = {
            "evaluation_id": evaluation_id,
            "file_name": safe_filename,
            "file_size": file_size,
            "file_path": dest_path,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "status": "uploaded",
            "crops": [],
            "needs_human_review": False,
            "review_reasons": [],
        }
        result = await db.sheets.insert_one(doc)

        uploaded.append(
            UploadedSheetInfo(
                sheet_id=str(result.inserted_id),
                file_name=safe_filename,
                file_size=file_size,
                status="uploaded",
            )
        )

    return UploadSheetsResponse(
        success=True,
        uploaded_sheets=uploaded,
        message=f"{len(uploaded)} sheet(s) uploaded successfully",
    )


# ---------------------------------------------------------------------------
# POST  /evaluations/{evaluation_id}/rubric  —  upload rubric document
# ---------------------------------------------------------------------------
@router.post("/evaluations/{evaluation_id}/rubric")
async def upload_rubric(
    evaluation_id: str,
    file: UploadFile = File(..., description="Rubric document (PDF/DOC/TXT)"),
):
    """Upload a rubric file for an evaluation."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    safe_filename = _sanitize_filename(file.filename, f"rubric_{uuid.uuid4().hex[:6]}.pdf")
    _validate_rubric_extension(safe_filename)

    rubric_dir = os.path.join(settings.upload_dir, evaluation_id, "rubric")
    os.makedirs(rubric_dir, exist_ok=True)

    dest_path = os.path.join(rubric_dir, safe_filename)
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(dest_path)

    # Parse components from the uploaded rubric file
    parsed_components = parse_rubric_file(dest_path)

    doc = {
        "evaluation_id": evaluation_id,
        "file_name": safe_filename,
        "file_size": file_size,
        "file_path": dest_path,
        "components": parsed_components,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

    # Upsert — one rubric per evaluation
    rubric_op = await db.rubrics.update_one(
        {"evaluation_id": evaluation_id},
        {"$set": doc},
        upsert=True,
    )
    rubric_id = str(rubric_op.upserted_id) if rubric_op.upserted_id else None
    if not rubric_id:
        existing_r = await db.rubrics.find_one({"evaluation_id": evaluation_id})
        if existing_r:
            rubric_id = str(existing_r["_id"])

    await db.evaluations.update_one(
        {"_id": ObjectId(evaluation_id)},
        {"$set": {"rubric_id": rubric_id, "rubric_file": safe_filename}},
    )

    return {
        "success": True,
        "file_name": safe_filename,
        "file_size": file_size,
        "components_count": len(parsed_components),
        "message": f"Rubric uploaded and parsed successfully ({len(parsed_components)} components)",
    }


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}/rubric
# ---------------------------------------------------------------------------
@router.get("/evaluations/{evaluation_id}/rubric")
async def get_rubric(evaluation_id: str):
    """Get the rubric metadata for an evaluation."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    doc = await db.rubrics.find_one({"evaluation_id": evaluation_id})

    if not doc:
        return {"success": False, "message": "No rubric found"}

    return {
        "success": True,
        "rubric": {
            "name": doc.get("file_name", "Unknown"),
            "size": doc.get("file_size", 0),
            "status": "uploaded",
        },
    }


# ---------------------------------------------------------------------------
# GET  /evaluations/{evaluation_id}/sheets  —  list uploaded sheets
# ---------------------------------------------------------------------------
@router.get(
    "/evaluations/{evaluation_id}/sheets",
    response_model=ListSheetsResponse,
)
async def list_sheets(evaluation_id: str):
    """List all uploaded sheets for an evaluation."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    cursor = db.sheets.find({"evaluation_id": evaluation_id})
    sheets: list[SheetMetadata] = []

    async for doc in cursor:
        sheets.append(
            SheetMetadata(
                id=str(doc["_id"]),
                evaluation_id=doc["evaluation_id"],
                file_name=doc.get("file_name", ""),
                file_size=doc.get("file_size", 0),
                file_path=doc.get("file_path", ""),
                uploaded_at=doc.get("uploaded_at", ""),
                status=doc.get("status", "uploaded"),
                crops=doc.get("crops", []),
                error=doc.get("error"),
                needs_human_review=doc.get("needs_human_review", False),
                review_reasons=doc.get("review_reasons", []),
            )
        )

    return ListSheetsResponse(success=True, sheets=sheets)


# ---------------------------------------------------------------------------
# DELETE  /evaluations/{evaluation_id}/sheets/{sheet_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/evaluations/{evaluation_id}/sheets/{sheet_id}",
    response_model=DeleteSheetResponse,
)
async def delete_sheet(evaluation_id: str, sheet_id: str):
    """Delete a specific sheet — removes file from disk and metadata from MongoDB."""
    if not ObjectId.is_valid(evaluation_id) or not ObjectId.is_valid(sheet_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    db = get_database()
    doc = await db.sheets.find_one({"_id": ObjectId(sheet_id), "evaluation_id": evaluation_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Sheet not found")

    # Remove file safely from disk
    file_path = doc.get("file_path", "")
    if file_path and os.path.exists(file_path):
        if _is_safe_path(settings.upload_dir, file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    await db.sheets.delete_one({"_id": ObjectId(sheet_id)})

    return DeleteSheetResponse(
        success=True,
        message=f"Sheet '{doc.get('file_name', sheet_id)}' deleted successfully",
    )


# ---------------------------------------------------------------------------
# DELETE  /evaluations/{evaluation_id}/rubric
# ---------------------------------------------------------------------------
@router.delete("/evaluations/{evaluation_id}/rubric")
async def delete_rubric(evaluation_id: str):
    """Delete the rubric for an evaluation — removes file from disk and metadata from MongoDB."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    doc = await db.rubrics.find_one({"evaluation_id": evaluation_id})
    if not doc:
        return {"success": True, "message": "No rubric found to delete"}

    # Remove file safely from disk
    file_path = doc.get("file_path", "")
    if file_path and os.path.exists(file_path):
        if _is_safe_path(settings.upload_dir, file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    await db.rubrics.delete_one({"evaluation_id": evaluation_id})
    await db.evaluations.update_one(
        {"_id": ObjectId(evaluation_id)},
        {"$unset": {"rubric_id": "", "rubric_file": ""}},
    )

    return {
        "success": True,
        "message": "Rubric deleted successfully",
    }
