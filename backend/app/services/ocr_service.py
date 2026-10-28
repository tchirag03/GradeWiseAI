"""
OCR Service.
Provides helper extraction methods for image digitization and transcription,
integrating with the Unified VLM pipeline.
"""
from typing import Optional, Dict, Any
from app.services.unified_vlm_service import get_unified_vlm_service


class OCRService:
    """Service wrapping handwriting extraction & transcription."""

    def __init__(self):
        self.vlm_service = get_unified_vlm_service()

    async def extract_text_from_sheet(
        self,
        evaluation_id: str,
        sheet_id: str,
    ) -> Dict[str, Any]:
        """Performs multimodal transcription and assessment for a sheet."""
        return await self.vlm_service.evaluate_sheet(evaluation_id, sheet_id)


_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service

