"""
Answer sheet schemas for upload and management.
Matches the frontend contract defined in api/sheets.ts.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# --- Status literal matching frontend + offline pipeline ---
SheetStatus = Literal[
    "uploaded",
    "preprocessing-pending",
    "preprocessing-processing",
    "preprocessing-completed",
    "preprocessing-failed",
    "ocr-pending",
    "ocr-processing",
    "ocr-completed",
    "ocr-failed",
    "transcribing-pending",
    "transcribing-processing",
    "transcribing-completed",
    "transcribing-failed",
    "structuring-pending",
    "structuring-processing",
    "structuring-completed",
    "structuring-failed",
    "grading-pending",
    "grading-processing",
    "grading-completed",
    "grading-failed",
    "evaluation-pending",
    "evaluation-processing",
    "evaluation-completed",
    "evaluation-failed",
    "review-needed",
]

CropType = Literal["text", "figure", "table", "math", "unknown"]


class SheetCrop(BaseModel):
    crop_id: str
    crop_type: CropType = "text"
    crop_path: str
    bbox: list[int] = Field(default_factory=list, description="[ymin, xmin, ymax, xmax]")
    question_hint: str | None = None
    transcription: str | None = None
    diagram_description: str | None = None


# --- Upload response (returned per-file after upload) ---
class UploadedSheetInfo(BaseModel):
    sheet_id: str
    file_name: str
    file_size: int
    status: SheetStatus = "uploaded"


class UploadSheetsResponse(BaseModel):
    success: bool = True
    uploaded_sheets: list[UploadedSheetInfo]
    message: str


# --- Full metadata (stored in MongoDB, returned by GET) ---
class SheetMetadata(BaseModel):
    id: str
    evaluation_id: str
    file_name: str
    file_size: int
    file_path: str
    uploaded_at: str  # ISO-8601 string
    status: SheetStatus = "uploaded"
    crops: list[SheetCrop] = Field(default_factory=list)
    needs_human_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)


class ListSheetsResponse(BaseModel):
    success: bool = True
    sheets: list[SheetMetadata]


# --- Delete ---
class DeleteSheetResponse(BaseModel):
    success: bool = True
    message: str
