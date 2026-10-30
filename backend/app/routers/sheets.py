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
    mode: str = "single_script",
):
    """Upload answer sheets for a given evaluation.

    • mode='single_script': Combines all uploaded files into 1 multi-page answer script.
    • mode='individual_files': Saves each uploaded file as an independent student sheet.
    """
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    evaluation = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    upload_dir = _ensure_upload_dir(evaluation_id)
    saved_files = []

    # Save all files to disk first
    for file in files:
        safe_filename = _sanitize_filename(file.filename, f"sheet_{uuid.uuid4().hex[:6]}.png")
        _validate_extension(safe_filename)

        dest_path = os.path.join(upload_dir, safe_filename)
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(safe_filename)
            safe_filename = f"{base}_{uuid.uuid4().hex[:6]}{ext}"
            dest_path = os.path.join(upload_dir, safe_filename)

        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        file_size = os.path.getsize(dest_path)
        saved_files.append({"name": safe_filename, "path": dest_path, "size": file_size})

    # Sort files chronologically/alphabetically by filename so pages are in natural order
    saved_files.sort(key=lambda x: x["name"])
    uploaded: list[UploadedSheetInfo] = []

    if mode == "single_script" and saved_files:
        # Check if an existing un-evaluated bundle already exists in this evaluation
        existing_bundle = await db.sheets.find_one({
            "evaluation_id": evaluation_id,
            "is_bundle": True,
            "status": "uploaded"
        })

        if existing_bundle:
            # Append new pages to existing bundle
            current_pages = existing_bundle.get("pages", [])
            start_num = len(current_pages) + 1
            for idx, sf in enumerate(saved_files):
                current_pages.append({
                    "page_number": start_num + idx,
                    "file_name": sf["name"],
                    "file_path": sf["path"],
                    "file_size": sf["size"],
                })
            new_total_size = sum(p.get("file_size", 0) for p in current_pages)
            first_name = current_pages[0]["file_name"]
            bundle_display_name = f"{first_name} (+{len(current_pages)-1} pages)"

            await db.sheets.update_one(
                {"_id": existing_bundle["_id"]},
                {
                    "$set": {
                        "pages": current_pages,
                        "page_count": len(current_pages),
                        "file_size": new_total_size,
                        "file_name": bundle_display_name,
                    }
                }
            )
            uploaded.append(
                UploadedSheetInfo(
                    sheet_id=str(existing_bundle["_id"]),
                    file_name=bundle_display_name,
                    file_size=new_total_size,
                    status="uploaded",
                    page_count=len(current_pages),
                    is_bundle=True,
                )
            )
        else:
            # Create a new combined multi-page script document
            pages_meta = [
                {
                    "page_number": idx + 1,
                    "file_name": sf["name"],
                    "file_path": sf["path"],
                    "file_size": sf["size"],
                }
                for idx, sf in enumerate(saved_files)
            ]
            first_name = saved_files[0]["name"]
            bundle_display_name = (
                f"{first_name} (+{len(saved_files)-1} pages)"
                if len(saved_files) > 1
                else first_name
            )
            total_size = sum(sf["size"] for sf in saved_files)

            doc = {
                "evaluation_id": evaluation_id,
                "file_name": bundle_display_name,
                "file_size": total_size,
                "file_path": saved_files[0]["path"],
                "is_bundle": True,
                "page_count": len(saved_files),
                "pages": pages_meta,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "status": "uploaded",
                "crops": [],
                "needs_human_review": False,
                "review_reasons": [],
            }
            res = await db.sheets.insert_one(doc)
            uploaded.append(
                UploadedSheetInfo(
                    sheet_id=str(res.inserted_id),
                    file_name=bundle_display_name,
                    file_size=total_size,
                    status="uploaded",
                    page_count=len(saved_files),
                    is_bundle=True,
                )
            )
    else:
        # Individual files mode
        for sf in saved_files:
            doc = {
                "evaluation_id": evaluation_id,
                "file_name": sf["name"],
                "file_size": sf["size"],
                "file_path": sf["path"],
                "is_bundle": False,
                "page_count": 1,
                "pages": [{
                    "page_number": 1,
                    "file_name": sf["name"],
                    "file_path": sf["path"],
                    "file_size": sf["size"],
                }],
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "status": "uploaded",
                "crops": [],
                "needs_human_review": False,
                "review_reasons": [],
            }
            res = await db.sheets.insert_one(doc)
            uploaded.append(
                UploadedSheetInfo(
                    sheet_id=str(res.inserted_id),
                    file_name=sf["name"],
                    file_size=sf["size"],
                    status="uploaded",
                    page_count=1,
                    is_bundle=False,
                )
            )

    return UploadSheetsResponse(
        success=True,
        uploaded_sheets=uploaded,
        message=f"{len(saved_files)} file(s) processed in mode '{mode}'",
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
                page_count=doc.get("page_count", len(doc.get("pages", [])) or 1),
                is_bundle=doc.get("is_bundle", False),
                pages=doc.get("pages", []),
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

# ---------------------------------------------------------------------------
# POST  /evaluations/{evaluation_id}/sheets/bundle  —  bundle all into 1 script
# ---------------------------------------------------------------------------
@router.post("/evaluations/{evaluation_id}/sheets/bundle")
async def bundle_sheets(evaluation_id: str):
    """Combines all uploaded sheets in an evaluation into a single multi-page script bundle."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    sheets = await db.sheets.find({"evaluation_id": evaluation_id}).sort("file_name", 1).to_list(100)
    if not sheets:
        raise HTTPException(status_code=400, detail="No sheets found to bundle")
    if len(sheets) == 1 and sheets[0].get("is_bundle"):
        return {"success": True, "message": "Already a bundle", "sheet_id": str(sheets[0]["_id"])}

    all_pages = []
    total_size = 0
    page_num = 1
    for s in sheets:
        if s.get("is_bundle") and s.get("pages"):
            for p in s["pages"]:
                all_pages.append({
                    "page_number": page_num,
                    "file_name": p.get("file_name"),
                    "file_path": p.get("file_path"),
                    "file_size": p.get("file_size", 0),
                })
                total_size += p.get("file_size", 0)
                page_num += 1
        else:
            all_pages.append({
                "page_number": page_num,
                "file_name": s.get("file_name"),
                "file_path": s.get("file_path"),
                "file_size": s.get("file_size", 0),
            })
            total_size += s.get("file_size", 0)
            page_num += 1

    first_file = all_pages[0]["file_name"]
    bundle_name = f"{first_file} (+{len(all_pages)-1} pages)" if len(all_pages) > 1 else first_file

    sheet_ids = [s["_id"] for s in sheets]
    await db.sheets.delete_many({"_id": {"$in": sheet_ids}})

    doc = {
        "evaluation_id": evaluation_id,
        "file_name": bundle_name,
        "file_size": total_size,
        "file_path": all_pages[0]["file_path"],
        "is_bundle": True,
        "page_count": len(all_pages),
        "pages": all_pages,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "status": "uploaded",
        "crops": [],
        "needs_human_review": False,
        "review_reasons": [],
    }
    result = await db.sheets.insert_one(doc)
    return {"success": True, "message": f"Successfully bundled {len(all_pages)} pages into 1 script", "sheet_id": str(result.inserted_id)}


# ---------------------------------------------------------------------------
# POST  /evaluations/{evaluation_id}/sheets/unbundle  —  split bundle into pages
# ---------------------------------------------------------------------------
@router.post("/evaluations/{evaluation_id}/sheets/unbundle")
async def unbundle_sheets(evaluation_id: str):
    """Splits multi-page bundles in the evaluation into separate single-page sheets."""
    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID format")

    db = get_database()
    sheets = await db.sheets.find({"evaluation_id": evaluation_id}).to_list(100)
    unbundled_count = 0

    for s in sheets:
        if s.get("is_bundle") and s.get("pages") and len(s["pages"]) > 1:
            pages = s["pages"]
            await db.sheets.delete_one({"_id": s["_id"]})
            for p in pages:
                doc = {
                    "evaluation_id": evaluation_id,
                    "file_name": p.get("file_name"),
                    "file_size": p.get("file_size", 0),
                    "file_path": p.get("file_path"),
                    "is_bundle": False,
                    "page_count": 1,
                    "pages": [p],
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "status": "uploaded",
                    "crops": [],
                    "needs_human_review": False,
                    "review_reasons": [],
                }
                await db.sheets.insert_one(doc)
                unbundled_count += 1

    return {"success": True, "message": f"Successfully unbundled into {unbundled_count} separate sheets"}
