"""
Pydantic models for answer-script documents.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EvaluationStep(BaseModel):
    component: str
    marks: float


class ScriptEvaluation(BaseModel):
    steps: list[EvaluationStep] = []
    total: float = 0.0


class CreateScriptRequest(BaseModel):
    student_id: str
    question_id: str
    text: str


class ScriptResponse(BaseModel):
    id: str = Field(..., alias="_id")
    student_id: str
    question_id: str
    text: str
    evaluation: Optional[ScriptEvaluation] = None
    status: str = "pending"
    created_at: datetime

    class Config:
        populate_by_name = True


class ScriptListResponse(BaseModel):
    total: int
    scripts: list[ScriptResponse]
