"""
Text structuring schemas.
Matches the frontend contract in api/structuring.ts.
"""
from pydantic import BaseModel
from typing import Literal, Optional

from app.schemas.common import ProcessingStatus


# --- Answer components ---

class AnswerStep(BaseModel):
    step_number: int
    description: str
    type: Literal["explanation", "code", "diagram", "calculation"]
    content: str


class CodeBlock(BaseModel):
    language: str = "python"
    code: str
    line_numbers: dict  # {"start": int, "end": int}


class StructuredAnswer(BaseModel):
    raw_text: str
    structured_steps: list[AnswerStep]
    identified_algorithm: str | None = None
    complexity: str | None = None
    keywords: list[str] = []
    code_blocks: list[CodeBlock] = []


class StructuredQuestion(BaseModel):
    question_number: int
    question_text: str
    answer: StructuredAnswer


class StructuredTextMetadata(BaseModel):
    total_questions: int
    total_steps: int
    average_complexity: str = "N/A"


class StructuredText(BaseModel):
    questions: list[StructuredQuestion]
    metadata: StructuredTextMetadata


# --- API response models ---

class StructuringStartResponse(BaseModel):
    success: bool = True
    job_id: str
    message: str
    total_sheets: int


class StructuringProgress(BaseModel):
    total: int
    completed: int
    failed: int
    percentage: int


class StructuringStatusResponse(BaseModel):
    success: bool = True
    status: ProcessingStatus
    progress: StructuringProgress
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None


class StructuringResultResponse(BaseModel):
    success: bool = True
    sheet_id: str
    status: ProcessingStatus
    result: StructuredText | None = None
    error: str | None = None
