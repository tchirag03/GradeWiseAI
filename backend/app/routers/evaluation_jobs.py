"""
Evaluation jobs router — enqueue evaluation tasks and poll status.
"""
from fastapi import APIRouter, HTTPException
from app.schemas.queue import StartEvaluationRequest, JobStatusResponse
from app.db.services import queue_service, status_service

router = APIRouter(prefix="/evaluation", tags=["Evaluation Jobs"])


@router.post("/start", response_model=JobStatusResponse, status_code=202)
async def start_evaluation(body: StartEvaluationRequest):
    """Enqueue an evaluation job and return its job_id."""
    job_id = await queue_service.enqueue_job(
        script_id=body.script_id,
        rubric_id=body.rubric_id,
    )
    return {"job_id": job_id, "status": "queued", "progress": 0}


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_status(job_id: str):
    """Poll the current status of an evaluation job."""
    data = await status_service.get_job_status(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return data
