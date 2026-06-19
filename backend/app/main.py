"""
Banking Cloud Log Analyser - FastAPI Application Entry Point
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
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.agents.graph import set_broadcast_callback

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    # --- Startup ---
    setup_logging("DEBUG" if settings.debug else "INFO")
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize database tables
    await init_db()
    logger.info("Database initialized")

    # Set WebSocket broadcast callback for the agent pipeline
    set_broadcast_callback(broadcast_event)

    # Start the scheduler for periodic log extraction
    start_scheduler()

    yield

    # --- Shutdown ---
    stop_scheduler()
    await close_db()
    logger.info("Application shut down")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent AI system for analyzing Azure cloud logs in banking infrastructure",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(logs_router)
app.include_router(incidents_router)
app.include_router(agents_router)
app.include_router(workflow_router)
app.include_router(export_router)
app.include_router(ws_router)
app.include_router(node_config_router)


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
    """
    Combined dashboard summary endpoint.
    Aggregates data from raw_logs, cloud_logs (segregated), incidents, and agents.
    """
    from sqlalchemy import select, func, desc
    from app.database import async_session
    from app.models.raw_log import RawLog
    from app.models.cloud_log import CloudLog
    from app.models.incident import Incident, PriorityLevel, IncidentStatus
    from app.models.agent_run import AgentRun, AgentRunStatus
    from app.services.scheduler_service import get_next_run_time

    async with async_session() as session:
        # Raw log stats (before segregation)
        total_raw = (await session.execute(select(func.count(RawLog.id)))).scalar() or 0
        pending_segregation = (await session.execute(
            select(func.count(RawLog.id)).where(RawLog.is_segregated == False)
        )).scalar() or 0
        segregated_count = total_raw - pending_segregation

        # Segregated log stats (cloud_logs — structured by Agent 1)
        total_logs = (await session.execute(select(func.count(CloudLog.id)))).scalar() or 0
        unprocessed = (await session.execute(
            select(func.count(CloudLog.id)).where(CloudLog.is_processed == False)
        )).scalar() or 0
        error_logs = (await session.execute(
            select(func.count(CloudLog.id)).where(CloudLog.level.in_(["ERROR", "CRITICAL"]))
        )).scalar() or 0

        # Incident stats
        total_incidents = (await session.execute(select(func.count(Incident.id)))).scalar() or 0
        open_incidents = (await session.execute(
            select(func.count(Incident.id)).where(Incident.status == IncidentStatus.OPEN)
        )).scalar() or 0
        high_priority = (await session.execute(
            select(func.count(Incident.id)).where(Incident.priority == PriorityLevel.HIGH)
        )).scalar() or 0
        medium_priority = (await session.execute(
            select(func.count(Incident.id)).where(Incident.priority == PriorityLevel.MEDIUM)
        )).scalar() or 0
        low_priority = (await session.execute(
            select(func.count(Incident.id)).where(Incident.priority == PriorityLevel.LOW)
        )).scalar() or 0

        # Last agent run
        last_run_result = await session.execute(
            select(AgentRun).order_by(desc(AgentRun.started_at)).limit(1)
        )
        last_run = last_run_result.scalar_one_or_none()

        # Total pipeline runs
        total_runs = (await session.execute(select(func.count(AgentRun.id)))).scalar() or 0

    return {
        "raw_logs": {
            "total": total_raw,
            "pending_segregation": pending_segregation,
            "segregated": segregated_count,
        },
        "logs": {
            "total": total_logs,
            "unprocessed": unprocessed,
            "errors": error_logs,
        },
        "incidents": {
            "total": total_incidents,
            "open": open_incidents,
            "high_priority": high_priority,
            "medium_priority": medium_priority,
            "low_priority": low_priority,
        },
        "pipeline": {
            "total_runs": total_runs,
            "is_running": last_run.status == AgentRunStatus.RUNNING if last_run else False,
            "last_run_status": last_run.status.value if last_run else None,
            "last_run_at": str(last_run.started_at) if last_run else None,
            "next_run_at": str(get_next_run_time()) if get_next_run_time() else None,
        },
    }

