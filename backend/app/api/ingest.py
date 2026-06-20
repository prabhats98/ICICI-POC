"""
Ingest API — Direct log injection and synthetic log simulation endpoints.
Allows bypassing Azure Monitor for local testing of the full pipeline.
"""

import uuid
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.database import async_session
from app.models.raw_log import RawLog
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["Ingest"])


class LogBatch(BaseModel):
    """Batch of raw log entries to inject."""
    source_system: str
    logs: list[dict[str, Any]]
    pipeline_run_id: str | None = None


class SimulateRequest(BaseModel):
    """Request to trigger the synthetic log generator."""
    count: int = 60
    spread_minutes: int = 30
    trigger_pipeline: bool = True


@router.post("/logs")
async def ingest_logs(batch: LogBatch):
    """
    Inject a batch of raw logs directly into the database.
    Bypasses Azure Monitor — useful for testing the pipeline locally.
    """
    run_id = batch.pipeline_run_id or str(uuid.uuid4())
    ids = []

    async with async_session() as session:
        for log_entry in batch.logs:
            message = (
                log_entry.get("message")
                or log_entry.get("ResultDescription")
                or str(log_entry)
            )[:5000]

            raw_log = RawLog(
                id=str(uuid.uuid4()),
                ingested_at=datetime.utcnow(),
                source_system=batch.source_system,
                raw_payload=log_entry,
                raw_text=message,
                is_preprocessed=False,
                pipeline_run_id=run_id,
            )
            session.add(raw_log)
            ids.append(raw_log.id)

        await session.commit()

    logger.info(f"Ingest API: Stored {len(ids)} logs from '{batch.source_system}'")
    return {
        "status": "ingested",
        "count": len(ids),
        "source_system": batch.source_system,
        "run_id": run_id,
    }


@router.post("/simulate")
async def simulate_logs(req: SimulateRequest, background_tasks: BackgroundTasks):
    """
    Generate synthetic Azure logs and inject them into the pipeline.

    Generates realistic logs from:
    - Azure Front Door (access, WAF, latency)
    - Azure Application Gateway (access, firewall, backend)
    - Azure API Management (gateway, rate-limit, timeout)

    Optionally triggers the full 8-agent pipeline after injection.
    """
    from app.services.synthetic_log_generator import generate_and_inject_logs

    # Generate and inject logs
    result = await generate_and_inject_logs(
        count=req.count,
        spread_minutes=req.spread_minutes,
    )

    if req.trigger_pipeline:
        background_tasks.add_task(_run_pipeline_after_inject)

    return {
        "status": "simulated",
        "logs_injected": result["total_injected"],
        "per_source": result["per_source"],
        "pipeline_triggered": req.trigger_pipeline,
        "message": (
            f"Generated {result['total_injected']} synthetic logs across "
            f"{len(result['per_source'])} Azure services. "
            + ("Pipeline started in background." if req.trigger_pipeline else "")
        ),
    }


@router.get("/stats")
async def ingest_stats():
    """Return counts of raw logs by source system."""
    from sqlalchemy import select, func
    from app.models.raw_log import RawLog

    async with async_session() as session:
        result = await session.execute(
            select(RawLog.source_system, func.count(RawLog.id).label("count"))
            .group_by(RawLog.source_system)
        )
        rows = result.all()

    return {
        "by_source": {row.source_system: row.count for row in rows},
        "total": sum(row.count for row in rows),
    }


async def _run_pipeline_after_inject():
    """Background task: run the pipeline after log injection."""
    try:
        from app.agents.graph import run_pipeline
        await run_pipeline(trigger_type="simulate")
    except Exception as e:
        logger.error(f"Pipeline run after inject failed: {e}")
