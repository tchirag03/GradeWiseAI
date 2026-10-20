"""
Scripts router — thin API layer for script CRUD.
All DB logic delegated to the repository.
"""
from fastapi import APIRouter, HTTPException, Query
from app.schemas.script import CreateScriptRequest, ScriptResponse, ScriptListResponse
from app.db.repositories import script_repo

router = APIRouter(prefix="/scripts", tags=["Scripts"])


@router.post("", response_model=ScriptResponse, status_code=201)
async def create_script(body: CreateScriptRequest):
    """Insert a new answer script."""
    doc = await script_repo.insert_script(
        student_id=body.student_id,
        question_id=body.question_id,
        text=body.text,
    )
    return doc


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(script_id: str):
    """Fetch a single script by ID."""
    doc = await script_repo.get_script(script_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Script not found")
    return doc


@router.get("", response_model=ScriptListResponse)
async def list_scripts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Paginated script listing."""
    docs, total = await script_repo.list_scripts(skip=skip, limit=limit)
    return {"total": total, "scripts": docs}
