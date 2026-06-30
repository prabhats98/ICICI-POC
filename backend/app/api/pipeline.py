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
async def manual_run(body: dict = {}):
    """Trigger a manual pipeline run with optional date range."""
    if not is_pipeline_enabled():
        return {"status": "error", "message": "Pipeline is disabled. Enable it first."}

    start_date = body.get("start_date")  # ISO format: "2026-06-20T00:00:00"
    end_date = body.get("end_date")      # ISO format: "2026-06-26T23:59:59"

    import asyncio
    asyncio.create_task(run_pipeline(
        trigger_type="manual",
        start_date=start_date,
        end_date=end_date,
    ))
    return {
        "status": "started",
        "message": f"Pipeline run started{f' ({start_date} to {end_date})' if start_date else ''}",
    }


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
