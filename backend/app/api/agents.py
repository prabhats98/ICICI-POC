"""
Agents API Router - Trigger and monitor the agent pipeline.
"""

import math
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent_run import AgentRun, AgentRunStatus
from app.schemas.agent_schemas import (
    AgentRunResponse,
    AgentRunListResponse,
    PipelineTriggerRequest,
    PipelineTriggerResponse,
)
from app.agents.graph import run_pipeline

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.post("/run", response_model=PipelineTriggerResponse)
async def trigger_pipeline(
    request: PipelineTriggerRequest,
    background_tasks: BackgroundTasks,
):
    """Manually trigger the agent pipeline."""
    import uuid

    run_id = uuid.uuid4()

    # Run pipeline in background
    background_tasks.add_task(run_pipeline, request.trigger_type)

    return PipelineTriggerResponse(
        run_id=run_id,
        status="started",
        message="Agent pipeline triggered successfully. Check /api/agents/history for results.",
    )


@router.get("/history", response_model=AgentRunListResponse)
async def list_agent_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    status: Optional[AgentRunStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    """List agent pipeline run history."""
    query = select(AgentRun)
    count_query = select(func.count(AgentRun.id))

    if status:
        query = query.where(AgentRun.status == status)
        count_query = count_query.where(AgentRun.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(desc(AgentRun.started_at)).offset(offset).limit(page_size)

    result = await db.execute(query)
    runs = result.scalars().all()

    return AgentRunListResponse(
        items=[AgentRunResponse.model_validate(run) for run in runs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/status")
async def get_pipeline_status(db: AsyncSession = Depends(get_db)):
    """Get the status of the most recent pipeline run."""
    result = await db.execute(
        select(AgentRun).order_by(desc(AgentRun.started_at)).limit(1)
    )
    latest_run = result.scalar_one_or_none()

    if not latest_run:
        return {
            "is_running": False,
            "last_run": None,
            "message": "No pipeline runs found",
        }

    return {
        "is_running": latest_run.status == AgentRunStatus.RUNNING,
        "last_run": AgentRunResponse.model_validate(latest_run),
        "message": f"Last run: {latest_run.status.value}",
    }