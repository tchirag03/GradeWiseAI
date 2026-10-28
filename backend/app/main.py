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
from app.core.mongodb import connect_db, close_db, get_database
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


async def recover_stale_evaluations() -> None:
    """
    On backend startup, reset any evaluations left in 'processing' status
    due to a previous server shutdown/restart so clients do not poll forever.
    """
    try:
        db = get_database()
        stale_evals = await db.evaluations.find({"status": "processing"}).to_list(length=None)
        for ev in stale_evals:
            ev_id = str(ev["_id"])
            await db.evaluations.update_one(
                {"_id": ev["_id"]},
                {
                    "$set": {
                        "status": "failed",
                        "pipeline_stage": "interrupted",
                        "error": "Server was restarted while pipeline was running. Please retry.",
                    }
                },
            )
            await db.sheets.update_many(
                {
                    "evaluation_id": ev_id,
                    "status": {
                        "$in": [
                            "preprocessing-pending",
                            "preprocessing-processing",
                            "transcribing-pending",
                            "transcribing-processing",
                            "grading-pending",
                            "grading-processing",
                        ]
                    },
                },
                {"$set": {"status": "failed", "error": "Interrupted by server restart"}},
            )
            print(f"[Startup] Cleaned up interrupted evaluation {ev_id} (marked as failed).")
    except Exception as exc:
        print(f"[Startup] Error checking stale evaluations: {exc}")


# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_db()
    await connect_redis()
    await connect_arq_pool()
    await ensure_indexes()
    await recover_stale_evaluations()

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

# Static file serving for uploads and evaluation logs
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount("/logs", StaticFiles(directory=settings.log_dir), name="logs")

# Register core application routers
app.include_router(evaluations.router, prefix="/api")
app.include_router(sheets.router, prefix="/api")
app.include_router(ocr.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")

# Register extended modular routers
app.include_router(scripts.router, prefix="/api")
app.include_router(evaluation_jobs.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(performance.router, prefix="/api")


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.version,
        "docs_url": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.version,
    }
