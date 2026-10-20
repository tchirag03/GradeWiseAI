"""
Pydantic models for rubric documents.
"""
from pydantic import BaseModel, Field


class RubricComponent(BaseModel):
    name: str
    marks: float
    model_answer: str = Field("", description="Ideal answer for this specific component or question")
    mark_bands: str = Field("", description="Explicit descriptors for scoring (e.g., '4-5: flawless, 2-3: arithmetic slip')")


class CreateRubricRequest(BaseModel):
    components: list[RubricComponent]


class RubricResponse(BaseModel):
    id: str = Field(..., alias="_id")
    components: list[RubricComponent]

    class Config:
        populate_by_name = True


class RubricListResponse(BaseModel):
    total: int
    rubrics: list[RubricResponse]
