"""
Settings and system configuration API routes.
"""
from fastapi import APIRouter
from app.schemas.settings import (
    SettingsRequest,
    SettingsResponse,
    ClearCacheResponse,
)

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """Get system settings"""
    return SettingsResponse(
        success=True,
        ocr_sensitivity="medium",
        cache_enabled=True
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(request: SettingsRequest):
    """Update system settings"""
    return SettingsResponse(
        success=True,
        ocr_sensitivity=request.ocr_sensitivity or "medium",
        cache_enabled=True
    )


@router.post("/clear-cache", response_model=ClearCacheResponse)
async def clear_cache():
    """Clear system cache"""
    return ClearCacheResponse(
        success=True,
        message="Cache cleared successfully",
        cleared_items=0
    )
