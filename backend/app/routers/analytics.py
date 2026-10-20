"""
Analytics router — exposes aggregation query results.
Integrates Redis caching for performance.
"""
from fastapi import APIRouter, Query
from app.db.queries import aggregation_queries
from app.db.services import cache_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/average")
async def average_marks():
    """Average marks per question (cached)."""
    key = "analytics:avg_marks"
    cached = await cache_service.get_cached(key)
    if cached:
        return cached
    data = await aggregation_queries.avg_marks_per_question()
    await cache_service.set_cached(key, data, ttl=120)
    return data


@router.get("/top-students")
async def top_students(limit: int = Query(10, ge=1, le=50)):
    """Top students by total evaluation score (cached)."""
    key = f"analytics:top_students:{limit}"
    cached = await cache_service.get_cached(key)
    if cached:
        return cached
    data = await aggregation_queries.top_students(limit=limit)
    await cache_service.set_cached(key, data, ttl=120)
    return data


@router.get("/weak-areas")
async def weak_areas(limit: int = Query(5, ge=1, le=20)):
    """Weakest rubric components (cached)."""
    key = f"analytics:weak_areas:{limit}"
    cached = await cache_service.get_cached(key)
    if cached:
        return cached
    data = await aggregation_queries.weakest_rubric_components(limit=limit)
    await cache_service.set_cached(key, data, ttl=120)
    return data
