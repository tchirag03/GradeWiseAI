"""
Pydantic models for student documents.
"""
from pydantic import BaseModel, Field


class CreateStudentRequest(BaseModel):
    name: str


class StudentResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str

    class Config:
        populate_by_name = True


class StudentListResponse(BaseModel):
    total: int
    students: list[StudentResponse]
