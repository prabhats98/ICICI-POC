"""
Azure Incident Log Pipeline — FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, close_db
from app.utils.logger import setup_logging
from app.api.logs import router as logs_router
from app.api.incidents import router as incidents_router
from app.api.agents import router as agents_router
from app.api.workflow import router as workflow_router
from app.api.export import router as export_router
from app.api.websocket import router as ws_router, broadcast_event
from app.api.node_config import router as node_config_router
from app.api.pipeline import router as pipeline_router
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.agents.graph import set_broadcast_callback

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    setup_logging("DEBUG" if settings.debug else "INFO")
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    await init_db()
    logger.info("Database initialized")

    set_broadcast_callback(broadcast_event)

    if settings.scheduler_enabled:
        start_scheduler()

    yield

    stop_scheduler()
    await close_db()
    logger.info("Application shut down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent AI system for analyzing Azure cloud logs in banking infrastructure",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(logs_router)
app.include_router(incidents_router)
app.include_router(agents_router)
app.include_router(workflow_router)
app.include_router(export_router)
app.include_router(ws_router)
app.include_router(node_config_router)
app.include_router(pipeline_router)


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
    }


@app.get("/api/dashboard", tags=["Dashboard"])
async def dashboard_summary():
    """Combined dashboard summary with P1/P2/P3 counts, resolution metrics."""
    from sqlalchemy import select, func, desc
    from app.database import async_session
    from app.models.raw_log import RawLog
    from app.models.cloud_log import CloudLog
    from app.models.incident import Incident, PriorityLevel, IncidentStatus
    from app.models.agent_run import AgentRun, AgentRunStatus
    from app.services.scheduler_service import get_next_run_time, is_pipeline_enabled

    async with async_session() as session:
        # Raw log stats
        total_raw = (await session.execute(select(func.count(RawLog.id)))).scalar() or 0
        pending_preprocess = (await session.execute(
            select(func.count(RawLog.id)).where(RawLog.is_preprocessed == False)
        )).scalar() or 0

        # Processed log stats
        total_logs = (await session.execute(select(func.count(CloudLog.id)))).scalar() or 0
        error_logs = (await session.execute(
            select(func.count(CloudLog.id)).where(CloudLog.level.in_(["ERROR", "CRITICAL"]))
        )).scalar() or 0

        # Incident stats
        total_incidents = (await session.execute(select(func.count(Incident.id)))).scalar() or 0
        open_incidents = (await session.execute(
            select(func.count(Incident.id)).where(Incident.status == IncidentStatus.OPEN)
        )).scalar() or 0
        resolved_incidents = (await session.execute(
            select(func.count(Incident.id)).where(Incident.status.in_([IncidentStatus.RESOLVED, IncidentStatus.CLOSED]))
        )).scalar() or 0
        p1_count = (await session.execute(
            select(func.count(Incident.id)).where(Incident.priority == PriorityLevel.P1)
        )).scalar() or 0
        p2_count = (await session.execute(
            select(func.count(Incident.id)).where(Incident.priority == PriorityLevel.P2)
        )).scalar() or 0
        p3_count = (await session.execute(
            select(func.count(Incident.id)).where(Incident.priority == PriorityLevel.P3)
        )).scalar() or 0

        # Avg resolution time
        avg_resolution = (await session.execute(
            select(func.avg(Incident.resolution_duration_minutes))
            .where(Incident.resolution_duration_minutes.isnot(None))
        )).scalar()

        # Last agent run
        last_run_result = await session.execute(
            select(AgentRun).order_by(desc(AgentRun.started_at)).limit(1)
        )
        last_run = last_run_result.scalar_one_or_none()
        total_runs = (await session.execute(select(func.count(AgentRun.id)))).scalar() or 0

    return {
        "raw_logs": {
            "total": total_raw,
            "pending_preprocess": pending_preprocess,
        },
        "logs": {
            "total": total_logs,
            "errors": error_logs,
        },
        "incidents": {
            "total": total_incidents,
            "open": open_incidents,
            "resolved": resolved_incidents,
            "p1": p1_count,
            "p2": p2_count,
            "p3": p3_count,
            "avg_resolution_minutes": round(avg_resolution, 1) if avg_resolution else None,
        },
        "pipeline": {
            "total_runs": total_runs,
            "enabled": is_pipeline_enabled(),
            "is_running": last_run.status == AgentRunStatus.RUNNING if last_run else False,
            "last_run_status": last_run.status.value if last_run else None,
            "last_run_at": str(last_run.started_at) if last_run else None,
            "last_run_duration": last_run.duration_seconds if last_run else None,
            "next_run_at": str(get_next_run_time()) if get_next_run_time() else None,
        },
    }
