"""
Pipeline Control API — on/off toggle, manual run, status, thresholds.
"""

import logging

from fastapi import APIRouter

from app.services.scheduler_service import (
    is_pipeline_enabled,
    set_pipeline_enabled,
    pause_scheduler,
    resume_scheduler,
    get_scheduler_status,
    get_next_run_time,
)
from app.agents.graph import run_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["Pipeline Control"])


@router.get("/status")
async def pipeline_status():
    """Get pipeline and scheduler status."""
    return get_scheduler_status()


@router.post("/toggle")
async def toggle_pipeline(body: dict = {}):
    """Toggle pipeline on or off."""
    enabled = body.get("enabled", not is_pipeline_enabled())
    set_pipeline_enabled(enabled)

    if enabled:
        resume_scheduler()
    else:
        pause_scheduler()

    return {
        "enabled": is_pipeline_enabled(),
        "message": f"Pipeline {'enabled' if enabled else 'disabled'}",
    }


@router.post("/run")
async def manual_run():
    """Trigger a manual pipeline run."""
    if not is_pipeline_enabled():
        return {"status": "error", "message": "Pipeline is disabled. Enable it first."}

    import asyncio
    asyncio.create_task(run_pipeline(trigger_type="manual"))
    return {"status": "started", "message": "Pipeline run started"}


@router.get("/thresholds")
async def get_thresholds():
    """Get notification threshold settings."""
    return {
        "p1_auto_email": True,
        "p2_auto_email": True,
        "p3_auto_email": False,
    }


@router.put("/thresholds")
async def update_thresholds(body: dict):
    """Update notification thresholds (placeholder for DB-stored config)."""
    return {"status": "updated", "thresholds": body}
