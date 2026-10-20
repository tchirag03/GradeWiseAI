"""
Common schemas and response models shared across all API endpoints.
"""
from pydantic import BaseModel
from typing import Literal, Optional


# Status enums
ProcessingStatus = Literal["pending", "running", "completed", "failed"]


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str


class StatusResponse(BaseModel):
    """Standard status response for async operations"""
    success: bool = True
    status: ProcessingStatus
    progress: dict | None = None


# ---------------------------------------------------------------------------
# OCR-specific response models  (match frontend api/ocr.ts)
# ---------------------------------------------------------------------------

class OCRStartResponse(BaseModel):
    """Response when OCR processing is started."""
    success: bool = True
    job_id: str
    message: str
    total_sheets: int


class OCRProgress(BaseModel):
    total: int
    completed: int
    failed: int
    percentage: int


class OCRStatusResponse(BaseModel):
    """Polling response for OCR progress."""
    success: bool = True
    status: ProcessingStatus
    progress: OCRProgress
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None


class OCRResultDetail(BaseModel):
    """Extracted text + metadata for a single sheet."""
    extracted_text: str
    confidence: float
    processing_time: int  # milliseconds


class OCRResultResponse(BaseModel):
    """Response for a single sheet's OCR result."""
    success: bool = True
    sheet_id: str
    status: ProcessingStatus
    result: OCRResultDetail | None = None
    error: str | None = None
