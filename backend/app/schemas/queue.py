"""
Pydantic models for evaluation queue requests/responses.
"""
from pydantic import BaseModel
from typing import Optional


class StartEvaluationRequest(BaseModel):
    script_id: str
    rubric_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # queued | processing | completed | failed
    progress: Optional[int] = None
    result: Optional[dict] = None
