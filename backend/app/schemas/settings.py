"""
Settings schemas for system configuration.
"""
from pydantic import BaseModel
from typing import Literal


class SettingsRequest(BaseModel):
    """Request schema for updating settings"""
    ocr_sensitivity: Literal["low", "medium", "high"] | None = None


class SettingsResponse(BaseModel):
    """Response schema for settings data"""
    success: bool = True
    ocr_sensitivity: str = "medium"
    cache_enabled: bool = True


class ClearCacheResponse(BaseModel):
    """Response schema for cache clearing"""
    success: bool = True
    message: str
    cleared_items: int = 0
