"""
Agents API — Pipeline trigger, status, and history endpoints.
"""

import logging
from fastapi import APIRouter
from sqlalchemy import select, desc, func

from app.database import async_session
from app.models.agent_run import AgentRun, AgentRunStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.post("/run")
async def trigger_run(body: dict = {}):
    """Trigger a manual pipeline run with optional time range filter."""
    import asyncio
    from app.agents.graph import run_pipeline
    asyncio.create_task(run_pipeline(
        trigger_type=body.get("trigger_type", "manual"),
        start_time=body.get("start_time"),
        end_time=body.get("end_time"),
    ))
    return {"status": "started", "message": "Pipeline run triggered"}


@router.post("/reset-and-run")
async def reset_and_run():
    """Reset pipeline state and run."""
    import asyncio
    from app.agents.graph import run_pipeline
    asyncio.create_task(run_pipeline(trigger_type="manual"))
    return {"status": "started", "message": "Pipeline reset and run triggered"}


@router.get("/status")
async def agent_status():
    """Get current pipeline status."""
    from app.services.scheduler_service import is_pipeline_enabled, get_next_run_time

    async with async_session() as session:
        result = await session.execute(
            select(AgentRun).order_by(desc(AgentRun.started_at)).limit(1)
        )
        last_run = result.scalar_one_or_none()

    return {
        "pipeline_enabled": is_pipeline_enabled(),
        "is_running": last_run.status == AgentRunStatus.RUNNING if last_run else False,
        "next_run_at": str(get_next_run_time()) if get_next_run_time() else None,
        "last_run": {
            "id": last_run.id,
            "status": last_run.status.value,
            "trigger_type": last_run.trigger_type,
            "started_at": str(last_run.started_at),
            "completed_at": str(last_run.completed_at) if last_run.completed_at else None,
            "duration_seconds": last_run.duration_seconds,
            "logs_processed": last_run.logs_processed,
            "incidents_created": last_run.incidents_created,
            "p1_count": last_run.p1_count,
            "p2_count": last_run.p2_count,
            "p3_count": last_run.p3_count,
            "emails_sent": last_run.emails_sent,
        } if last_run else None,
    }


@router.get("/history")
async def agent_history(page: int = 1, page_size: int = 10):
    """Get pipeline run history."""
    async with async_session() as session:
        total = (await session.execute(select(func.count(AgentRun.id)))).scalar() or 0

        result = await session.execute(
            select(AgentRun)
            .order_by(desc(AgentRun.started_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        runs = result.scalars().all()

    return {
        "items": [
            {
                "id": r.id,
                "agent_name": r.agent_name,
                "status": r.status.value,
                "trigger_type": r.trigger_type,
                "started_at": str(r.started_at),
                "completed_at": str(r.completed_at) if r.completed_at else None,
                "duration_seconds": r.duration_seconds,
                "logs_processed": r.logs_processed,
                "incidents_created": r.incidents_created,
                "p1_count": r.p1_count,
                "p2_count": r.p2_count,
                "p3_count": r.p3_count,
                "emails_sent": r.emails_sent,
                "error_message": r.error_message,
            }
            for r in runs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }