"""
Analytics API — Endpoints for incident trends, service breakdowns,
error distributions, notification history, and recurring issues.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select, func, desc, and_
from sqlalchemy.sql.expression import cast
from sqlalchemy import Date

from app.database import async_session
from app.models.incident import Incident, PriorityLevel, IncidentStatus
from app.models.cloud_log import CloudLog
from app.models.agent_run import AgentRun

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/incident-trend")
async def incident_trend(days: int = Query(7, ge=1, le=90)):
    """
    Incidents per day for the past N days, broken down by priority.
    Returns a time-series suitable for line/bar charts.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with async_session() as session:
        # Total incidents per day
        result = await session.execute(
            select(
                func.date_trunc("day", Incident.created_at).label("day"),
                Incident.priority,
                func.count(Incident.id).label("count"),
            )
            .where(Incident.created_at >= cutoff)
            .group_by("day", Incident.priority)
            .order_by("day")
        )
        rows = result.all()

    # Build per-day structure
    days_map: dict[str, dict] = {}
    for row in rows:
        day_str = row.day.strftime("%Y-%m-%d") if row.day else "unknown"
        if day_str not in days_map:
            days_map[day_str] = {"date": day_str, "total": 0, "P1": 0, "P2": 0, "P3": 0}
        priority_key = row.priority.value if hasattr(row.priority, "value") else str(row.priority)
        days_map[day_str][priority_key] = days_map[day_str].get(priority_key, 0) + row.count
        days_map[day_str]["total"] += row.count

    # Fill in missing days with zeros
    all_days = []
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        all_days.append(days_map.get(d, {"date": d, "total": 0, "P1": 0, "P2": 0, "P3": 0}))

    return {"days": days, "data": all_days}


@router.get("/service-breakdown")
async def service_breakdown():
    """
    Incident counts per Azure service (Front Door, App Gateway, APIM).
    Broken down by priority and status.
    """
    async with async_session() as session:
        result = await session.execute(
            select(
                Incident.source_service,
                Incident.priority,
                Incident.status,
                func.count(Incident.id).label("count"),
            )
            .where(Incident.source_service.isnot(None))
            .group_by(Incident.source_service, Incident.priority, Incident.status)
            .order_by(Incident.source_service)
        )
        rows = result.all()

    # Aggregate by service
    services: dict[str, dict] = {}
    for row in rows:
        svc = row.source_service or "unknown"
        if svc not in services:
            services[svc] = {
                "service": svc,
                "total": 0,
                "P1": 0, "P2": 0, "P3": 0,
                "open": 0, "resolved": 0,
            }
        prio = row.priority.value if hasattr(row.priority, "value") else str(row.priority)
        status = row.status.value if hasattr(row.status, "value") else str(row.status)
        services[svc][prio] = services[svc].get(prio, 0) + row.count
        services[svc]["total"] += row.count
        if status in ("OPEN", "IN_PROGRESS", "ACKNOWLEDGED"):
            services[svc]["open"] += row.count
        elif status in ("RESOLVED", "CLOSED"):
            services[svc]["resolved"] += row.count

    return {"services": list(services.values())}


@router.get("/error-distribution")
async def error_distribution():
    """Incident count by category (Security, Performance, Availability, etc.)"""
    async with async_session() as session:
        result = await session.execute(
            select(
                Incident.category,
                func.count(Incident.id).label("count"),
            )
            .group_by(Incident.category)
            .order_by(desc("count"))
        )
        rows = result.all()

    total = sum(r.count for r in rows)
    return {
        "total": total,
        "distribution": [
            {
                "category": r.category or "Unknown",
                "count": r.count,
                "percentage": round(r.count / total * 100, 1) if total else 0,
            }
            for r in rows
        ],
    }


@router.get("/notification-history")
async def notification_history(limit: int = Query(50, ge=1, le=200)):
    """Recent incidents where email notifications were sent."""
    async with async_session() as session:
        result = await session.execute(
            select(Incident)
            .where(Incident.email_sent == True)
            .order_by(desc(Incident.email_sent_at))
            .limit(limit)
        )
        incidents = result.scalars().all()

    return {
        "total_notifications": len(incidents),
        "notifications": [
            {
                "incident_id": inc.id,
                "title": inc.title,
                "priority": inc.priority.value if inc.priority else None,
                "category": inc.category,
                "source_service": inc.source_service,
                "email_sent_at": inc.email_sent_at.isoformat() if inc.email_sent_at else None,
                "email_recipient": inc.email_recipient,
                "status": inc.status.value if inc.status else None,
            }
            for inc in incidents
        ],
    }


@router.get("/top-issues")
async def top_issues(limit: int = Query(10, ge=1, le=50)):
    """
    Top recurring issue titles by frequency.
    Helps identify patterns in the infrastructure.
    """
    async with async_session() as session:
        result = await session.execute(
            select(
                Incident.title,
                Incident.category,
                Incident.source_service,
                func.count(Incident.id).label("count"),
                func.max(Incident.created_at).label("last_seen"),
            )
            .group_by(Incident.title, Incident.category, Incident.source_service)
            .order_by(desc("count"))
            .limit(limit)
        )
        rows = result.all()

    return {
        "top_issues": [
            {
                "title": r.title,
                "category": r.category,
                "source_service": r.source_service,
                "count": r.count,
                "last_seen": r.last_seen.isoformat() if r.last_seen else None,
            }
            for r in rows
        ]
    }


@router.get("/log-volume")
async def log_volume(days: int = Query(7, ge=1, le=30)):
    """Raw and processed log volume over time."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with async_session() as session:
        result = await session.execute(
            select(
                func.date_trunc("day", CloudLog.created_at).label("day"),
                CloudLog.level,
                func.count(CloudLog.id).label("count"),
            )
            .where(CloudLog.created_at >= cutoff)
            .group_by("day", CloudLog.level)
            .order_by("day")
        )
        rows = result.all()

    days_map: dict[str, dict] = {}
    for row in rows:
        day_str = row.day.strftime("%Y-%m-%d") if row.day else "unknown"
        if day_str not in days_map:
            days_map[day_str] = {"date": day_str, "total": 0, "ERROR": 0, "WARNING": 0, "INFO": 0, "CRITICAL": 0}
        level = str(row.level)
        days_map[day_str][level] = days_map[day_str].get(level, 0) + row.count
        days_map[day_str]["total"] += row.count

    all_days = []
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        all_days.append(days_map.get(d, {"date": d, "total": 0, "ERROR": 0, "WARNING": 0, "INFO": 0, "CRITICAL": 0}))

    return {"days": days, "data": all_days}


@router.get("/pipeline-runs")
async def pipeline_runs(limit: int = Query(20, ge=1, le=100)):
    """Recent pipeline run history with stats."""
    async with async_session() as session:
        result = await session.execute(
            select(AgentRun)
            .order_by(desc(AgentRun.started_at))
            .limit(limit)
        )
        runs = result.scalars().all()

    return {
        "runs": [
            {
                "id": r.id,
                "status": r.status.value if r.status else None,
                "trigger_type": r.trigger_type,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "duration_seconds": r.duration_seconds,
                "logs_processed": r.logs_processed,
                "incidents_created": r.incidents_created,
                "p1_count": r.p1_count,
                "p2_count": r.p2_count,
                "p3_count": r.p3_count,
                "emails_sent": r.emails_sent,
                "sources_collected": r.sources_collected,
                "error_message": r.error_message,
            }
            for r in runs
        ]
    }
