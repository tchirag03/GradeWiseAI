"""
SLM evaluation schemas.
Matches the OCR / Structuring pattern for consistency.
"""
from pydantic import BaseModel
from typing import Optional

from app.schemas.common import ProcessingStatus


# --- Score components ---

class ComponentScore(BaseModel):
    """Score for a single rubric component."""
    component: str
    marks_awarded: float
    max_marks: float
    feedback: str
    model_answer: str = ""


class QuestionScore(BaseModel):
    """Evaluation result for a single question."""
    question_number: int
    question_text: str
    component_scores: list[ComponentScore] = []
    total_marks: float = 0.0
    max_marks: float = 0.0
    feedback: str = ""
    grade_context: str = ""
    evaluation_method: str = "model"


class SLMEvaluationResult(BaseModel):
    """Full evaluation result for a sheet."""
    questions: list[QuestionScore]
    total_score: float
    max_score: float
    percentage: float
    grade: str


# --- API response models ---

class SLMStartResponse(BaseModel):
    success: bool = True
    job_id: str
    message: str
    total_sheets: int


class SLMProgress(BaseModel):
    total: int
    completed: int
    failed: int
    percentage: int


class SLMStatusResponse(BaseModel):
    success: bool = True
    status: ProcessingStatus
    progress: SLMProgress
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None


class SLMResultResponse(BaseModel):
    success: bool = True
    sheet_id: str
    status: ProcessingStatus
    result: SLMEvaluationResult | None = None
    error: str | None = None
