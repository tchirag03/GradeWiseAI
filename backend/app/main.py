"""
FastAPI application entry point.
"""
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.mongodb import connect_db, close_db
from app.core.redis_client import connect_redis, close_redis
from app.core.arq_pool import connect_arq_pool, close_arq_pool
from app.db.queries.index_setup import ensure_indexes
from app.db.services.queue_service import start_worker
from app.services.unified_vlm_service import get_unified_vlm_service

from app.routers import (
    evaluations,
    sheets,
    ocr,
    results,
    export,
    pipeline,
    settings as settings_router,
)
from app.routers import scripts, evaluation_jobs, analytics, performance


# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_db()
    await connect_redis()
    await connect_arq_pool()
    await ensure_indexes()

    # Initialise offline unified VLM pipeline singleton
    get_unified_vlm_service()

    worker_task = asyncio.create_task(start_worker())
    yield
    # Shutdown
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await close_arq_pool()
    await close_redis()
    await close_db()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Modular NoSQL-Based Evaluation Data Management System",
    lifespan=lifespan,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure required directories exist before mounting
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.log_dir, exist_ok=True)

# Mount uploads directory for image inspection
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# ---------- Active routers ----------
app.include_router(evaluations.router, prefix=settings.api_prefix)
app.include_router(sheets.router, prefix=settings.api_prefix)
app.include_router(ocr.router, prefix=settings.api_prefix)
app.include_router(results.router, prefix=settings.api_prefix)
app.include_router(export.router, prefix=settings.api_prefix)
app.include_router(pipeline.router, prefix=settings.api_prefix)
app.include_router(settings_router.router, prefix=settings.api_prefix)

# ---------- New routers ----------
app.include_router(scripts.router, prefix=settings.api_prefix)
app.include_router(evaluation_jobs.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)
app.include_router(performance.router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Sustainable AI Assessment Platform API",
        "version": settings.version,
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
