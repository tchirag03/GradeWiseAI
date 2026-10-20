"""
Pydantic models for analytics responses.
"""
from pydantic import BaseModel


class AvgMarksResponse(BaseModel):
    question_id: str
    average: float


class TopStudentEntry(BaseModel):
    student_id: str
    total: float


class WeakAreaEntry(BaseModel):
    component: str
    average_marks: float


class PerformanceReport(BaseModel):
    student_id: str
    total_scripts: int
    average_score: float
    breakdown: list[dict]
