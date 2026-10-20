"""
Evaluation management schemas for CRUD operations.
"""
from pydantic import BaseModel
from typing import Literal


class CreateEvaluationRequest(BaseModel):
    """Request schema for creating a new evaluation"""
    name: str
    subject: str
    max_marks: int
    answer_type: Literal["printed", "handwritten"] = "printed"


class EvaluationResponse(BaseModel):
    """Response schema for evaluation data"""
    id: str
    name: str
    subject: str
    max_marks: int
    answer_type: str
    status: str = "draft"
    pipeline_stage: str | None = None


class EvaluationListResponse(BaseModel):
    """Response schema for listing evaluations"""
    success: bool = True
    evaluations: list[EvaluationResponse]


class DeleteEvaluationResponse(BaseModel):
    """Response schema for deletion"""
    success: bool = True
    deleted: str
    message: str
