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


@router.get("/mttr")
async def mean_time_to_resolution():
    """Mean Time To Resolution overall and by priority."""
    async with async_session() as session:
        # Overall MTTR
        overall = (await session.execute(
            select(func.avg(Incident.resolution_duration_minutes))
            .where(Incident.resolution_duration_minutes.isnot(None))
        )).scalar()

        # Per-priority MTTR
        result = await session.execute(
            select(
                Incident.priority,
                func.avg(Incident.resolution_duration_minutes).label("avg_minutes"),
                func.count(Incident.id).label("resolved_count"),
            )
            .where(Incident.resolution_duration_minutes.isnot(None))
            .group_by(Incident.priority)
        )
        rows = result.all()

    return {
        "overall_avg_minutes": round(overall, 1) if overall else None,
        "by_priority": {
            (r.priority.value if hasattr(r.priority, "value") else str(r.priority)): {
                "avg_minutes": round(r.avg_minutes, 1) if r.avg_minutes else None,
                "resolved_count": r.resolved_count,
            }
            for r in rows
        },
    }


@router.get("/golden-signals")
async def golden_signals():
    """
    Google SRE Golden Signals: Latency, Traffic, Errors, Saturation.
    Computed from existing data as proxy metrics.
    """
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)
    last_1h = now - timedelta(hours=1)
    prev_24h_start = now - timedelta(hours=48)
    prev_24h_end = now - timedelta(hours=24)

    async with async_session() as session:
        # --- Latency: avg pipeline run duration (last 24h) ---
        latency_current = (await session.execute(
            select(func.avg(AgentRun.duration_seconds))
            .where(AgentRun.started_at >= last_24h)
            .where(AgentRun.duration_seconds.isnot(None))
        )).scalar()
        latency_prev = (await session.execute(
            select(func.avg(AgentRun.duration_seconds))
            .where(and_(AgentRun.started_at >= prev_24h_start, AgentRun.started_at < prev_24h_end))
            .where(AgentRun.duration_seconds.isnot(None))
        )).scalar()

        # --- Traffic: logs ingested per hour (last 1h vs prev 1h) ---
        traffic_current = (await session.execute(
            select(func.count(CloudLog.id))
            .where(CloudLog.created_at >= last_1h)
        )).scalar() or 0
        traffic_prev = (await session.execute(
            select(func.count(CloudLog.id))
            .where(and_(CloudLog.created_at >= last_1h - timedelta(hours=1), CloudLog.created_at < last_1h))
        )).scalar() or 0

        # --- Errors: error rate (ERROR+CRITICAL logs / total logs, last 24h) ---
        total_logs_24h = (await session.execute(
            select(func.count(CloudLog.id))
            .where(CloudLog.created_at >= last_24h)
        )).scalar() or 0
        error_logs_24h = (await session.execute(
            select(func.count(CloudLog.id))
            .where(CloudLog.created_at >= last_24h)
            .where(CloudLog.level.in_(["ERROR", "CRITICAL"]))
        )).scalar() or 0
        error_rate = round((error_logs_24h / total_logs_24h * 100), 2) if total_logs_24h > 0 else 0

        # Previous period error rate
        total_logs_prev = (await session.execute(
            select(func.count(CloudLog.id))
            .where(and_(CloudLog.created_at >= prev_24h_start, CloudLog.created_at < prev_24h_end))
        )).scalar() or 0
        error_logs_prev = (await session.execute(
            select(func.count(CloudLog.id))
            .where(and_(CloudLog.created_at >= prev_24h_start, CloudLog.created_at < prev_24h_end))
            .where(CloudLog.level.in_(["ERROR", "CRITICAL"]))
        )).scalar() or 0
        error_rate_prev = round((error_logs_prev / total_logs_prev * 100), 2) if total_logs_prev > 0 else 0

        # --- Saturation: open P1 incidents as % of threshold (threshold=10) ---
        open_p1 = (await session.execute(
            select(func.count(Incident.id))
            .where(Incident.priority == PriorityLevel.P1)
            .where(Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS]))
        )).scalar() or 0

        # Hourly traffic for sparklines (last 24h)
        hourly_traffic = []
        for h in range(24):
            h_start = now - timedelta(hours=24 - h)
            h_end = now - timedelta(hours=23 - h)
            cnt = (await session.execute(
                select(func.count(CloudLog.id))
                .where(and_(CloudLog.created_at >= h_start, CloudLog.created_at < h_end))
            )).scalar() or 0
            hourly_traffic.append(cnt)

    def calc_delta(current, prev):
        if prev and prev > 0 and current is not None:
            return round(((current - prev) / prev) * 100, 1)
        return 0

    saturation_threshold = 10
    saturation_pct = min(round((open_p1 / saturation_threshold) * 100, 1), 100) if saturation_threshold > 0 else 0

    return {
        "latency": {
            "value": round(latency_current, 1) if latency_current else 0,
            "unit": "s",
            "delta_pct": calc_delta(latency_current, latency_prev),
            "label": "Avg Pipeline Duration",
        },
        "traffic": {
            "value": traffic_current,
            "unit": "logs/hr",
            "delta_pct": calc_delta(traffic_current, traffic_prev),
            "label": "Log Throughput",
            "sparkline": hourly_traffic,
        },
        "errors": {
            "value": error_rate,
            "unit": "%",
            "delta_pct": calc_delta(error_rate, error_rate_prev),
            "label": "Error Rate",
            "total_errors": error_logs_24h,
            "total_logs": total_logs_24h,
        },
        "saturation": {
            "value": saturation_pct,
            "unit": "%",
            "delta_pct": 0,
            "label": "P1 Saturation",
            "open_p1": open_p1,
            "threshold": saturation_threshold,
        },
    }


@router.get("/system-health")
async def system_health():
    """
    Composite system health score (0-100) computed from:
    - Open P1 count penalty
    - Error rate penalty
    - Pipeline success rate bonus
    - MTTR penalty
    """
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)

    async with async_session() as session:
        # Open P1s
        open_p1 = (await session.execute(
            select(func.count(Incident.id))
            .where(Incident.priority == PriorityLevel.P1)
            .where(Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS]))
        )).scalar() or 0

        # Open P2s
        open_p2 = (await session.execute(
            select(func.count(Incident.id))
            .where(Incident.priority == PriorityLevel.P2)
            .where(Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS]))
        )).scalar() or 0

        # Error rate (24h)
        total_logs = (await session.execute(
            select(func.count(CloudLog.id)).where(CloudLog.created_at >= last_24h)
        )).scalar() or 0
        error_logs = (await session.execute(
            select(func.count(CloudLog.id))
            .where(CloudLog.created_at >= last_24h)
            .where(CloudLog.level.in_(["ERROR", "CRITICAL"]))
        )).scalar() or 0
        error_rate = (error_logs / total_logs * 100) if total_logs > 0 else 0

        # Pipeline success rate (last 10 runs)
        runs = (await session.execute(
            select(AgentRun.status).order_by(desc(AgentRun.started_at)).limit(10)
        )).scalars().all()
        total_runs = len(runs)
        success_runs = sum(1 for r in runs if r and r.value == "SUCCESS")
        pipeline_rate = (success_runs / total_runs * 100) if total_runs > 0 else 100

        # Avg MTTR
        avg_mttr = (await session.execute(
            select(func.avg(Incident.resolution_duration_minutes))
            .where(Incident.resolution_duration_minutes.isnot(None))
        )).scalar()

    # Compute health score
    score = 100.0
    score -= min(open_p1 * 15, 45)   # Each open P1 costs 15pts, max 45
    score -= min(open_p2 * 5, 20)    # Each open P2 costs 5pts, max 20
    score -= min(error_rate * 2, 20)  # Error rate penalty, max 20
    score += (pipeline_rate - 50) * 0.2 if pipeline_rate > 50 else -(50 - pipeline_rate) * 0.3
    if avg_mttr and avg_mttr > 60:
        score -= min((avg_mttr - 60) * 0.1, 10)  # Slow MTTR penalty

    score = max(0, min(100, round(score)))

    if score >= 80:
        status = "HEALTHY"
    elif score >= 50:
        status = "DEGRADED"
    else:
        status = "CRITICAL"

    return {
        "score": score,
        "status": status,
        "factors": {
            "open_p1": open_p1,
            "open_p2": open_p2,
            "error_rate": round(error_rate, 2),
            "pipeline_success_rate": round(pipeline_rate, 1),
            "avg_mttr_minutes": round(avg_mttr, 1) if avg_mttr else None,
        },
    }


@router.get("/slo-status")
async def slo_status():
    """
    SLO compliance and error budget tracking.
    Target: 99.5% of incidents resolved within SLA.
    """
    slo_target = 99.5  # configurable later

    async with async_session() as session:
        # Total incidents (last 30 days)
        cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
        total = (await session.execute(
            select(func.count(Incident.id)).where(Incident.created_at >= cutoff_30d)
        )).scalar() or 0

        # Resolved incidents
        resolved = (await session.execute(
            select(func.count(Incident.id))
            .where(Incident.created_at >= cutoff_30d)
            .where(Incident.status.in_([IncidentStatus.RESOLVED, IncidentStatus.CLOSED]))
        )).scalar() or 0

        # Count SLA VIOLATIONS: resolved incidents that EXCEEDED their target
        # P1 > 30m, P2 > 60m, P3 > 120m
        sla_violations = 0
        for prio, target_min in [("P1", 30), ("P2", 60), ("P3", 120)]:
            cnt = (await session.execute(
                select(func.count(Incident.id))
                .where(Incident.created_at >= cutoff_30d)
                .where(Incident.priority == PriorityLevel[prio])
                .where(Incident.status.in_([IncidentStatus.RESOLVED, IncidentStatus.CLOSED]))
                .where(Incident.resolution_duration_minutes.isnot(None))
                .where(Incident.resolution_duration_minutes > target_min)
            )).scalar() or 0
            sla_violations += cnt

    # SLO = (total - violations) / total
    # Open incidents are NOT violations (still within their SLA window)
    within_sla = total - sla_violations
    compliance = round((within_sla / total * 100), 2) if total > 0 else 100.0
    error_budget_total = 100.0 - slo_target  # 0.5%
    error_budget_used = max(0, round(100.0 - compliance, 2)) if total > 0 else 0
    error_budget_remaining = max(0, round(error_budget_total - error_budget_used, 2))
    burn_rate = round(error_budget_used / error_budget_total, 2) if error_budget_total > 0 else 0

    return {
        "target_pct": slo_target,
        "compliance_pct": compliance,
        "total_incidents": total,
        "within_sla": within_sla,
        "sla_violations": sla_violations,
        "resolved_count": resolved,
        "error_budget_total_pct": error_budget_total,
        "error_budget_used_pct": round(error_budget_used, 2),
        "error_budget_remaining_pct": error_budget_remaining,
        "burn_rate": burn_rate,
    }



@router.get("/service-uptime")
async def service_uptime(days: int = Query(30, ge=7, le=90)):
    """
    Per-service daily incident severity for uptime heatmap.
    Returns a grid: date × service → max_severity + incident_count.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    services_list = ["azure-front-door", "azure-app-gateway", "azure-apim", "azure-vm"]

    async with async_session() as session:
        result = await session.execute(
            select(
                func.date_trunc("day", Incident.created_at).label("day"),
                Incident.source_service,
                Incident.priority,
                func.count(Incident.id).label("count"),
            )
            .where(Incident.created_at >= cutoff)
            .where(Incident.source_service.in_(services_list))
            .group_by("day", Incident.source_service, Incident.priority)
            .order_by("day")
        )
        rows = result.all()

    # Build grid
    grid: dict[str, dict[str, dict]] = {}
    for row in rows:
        day_str = row.day.strftime("%Y-%m-%d") if row.day else "unknown"
        svc = row.source_service
        prio = row.priority.value if hasattr(row.priority, "value") else str(row.priority)
        key = f"{day_str}|{svc}"
        if key not in grid:
            grid[key] = {"date": day_str, "service": svc, "count": 0, "max_severity": "P3", "P1": 0, "P2": 0, "P3": 0}
        grid[key][prio] = grid[key].get(prio, 0) + row.count
        grid[key]["count"] += row.count
        # Track max severity
        severity_order = {"P1": 0, "P2": 1, "P3": 2}
        if severity_order.get(prio, 2) < severity_order.get(grid[key]["max_severity"], 2):
            grid[key]["max_severity"] = prio

    # Fill in all days × services
    heatmap = []
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        for svc in services_list:
            key = f"{d}|{svc}"
            if key in grid:
                heatmap.append(grid[key])
            else:
                heatmap.append({"date": d, "service": svc, "count": 0, "max_severity": None, "P1": 0, "P2": 0, "P3": 0})

    return {"days": days, "services": services_list, "heatmap": heatmap}


@router.get("/kpi-trends")
async def kpi_trends(days: int = Query(7, ge=3, le=30)):
    """
    Daily KPI values for sparkline trends in dashboard cards.
    Returns per-day: total, open, P1, P2, P3, resolved, pipeline_runs.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with async_session() as session:
        # Incidents per day by priority
        inc_result = await session.execute(
            select(
                func.date_trunc("day", Incident.created_at).label("day"),
                Incident.priority,
                Incident.status,
                func.count(Incident.id).label("count"),
            )
            .where(Incident.created_at >= cutoff)
            .group_by("day", Incident.priority, Incident.status)
            .order_by("day")
        )
        inc_rows = inc_result.all()

        # Pipeline runs per day
        run_result = await session.execute(
            select(
                func.date_trunc("day", AgentRun.started_at).label("day"),
                func.count(AgentRun.id).label("count"),
            )
            .where(AgentRun.started_at >= cutoff)
            .group_by("day")
            .order_by("day")
        )
        run_rows = run_result.all()

    # Build per-day map
    days_map: dict[str, dict] = {}
    for row in inc_rows:
        day_str = row.day.strftime("%Y-%m-%d") if row.day else "unknown"
        if day_str not in days_map:
            days_map[day_str] = {"date": day_str, "total": 0, "open": 0, "P1": 0, "P2": 0, "P3": 0, "resolved": 0, "pipeline_runs": 0}
        prio = row.priority.value if hasattr(row.priority, "value") else str(row.priority)
        status = row.status.value if hasattr(row.status, "value") else str(row.status)
        days_map[day_str][prio] = days_map[day_str].get(prio, 0) + row.count
        days_map[day_str]["total"] += row.count
        if status in ("OPEN", "IN_PROGRESS", "ACKNOWLEDGED"):
            days_map[day_str]["open"] += row.count
        elif status in ("RESOLVED", "CLOSED"):
            days_map[day_str]["resolved"] += row.count

    for row in run_rows:
        day_str = row.day.strftime("%Y-%m-%d") if row.day else "unknown"
        if day_str not in days_map:
            days_map[day_str] = {"date": day_str, "total": 0, "open": 0, "P1": 0, "P2": 0, "P3": 0, "resolved": 0, "pipeline_runs": 0}
        days_map[day_str]["pipeline_runs"] = row.count

    # Fill all days
    all_days = []
    for i in range(days):
        d = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        all_days.append(days_map.get(d, {"date": d, "total": 0, "open": 0, "P1": 0, "P2": 0, "P3": 0, "resolved": 0, "pipeline_runs": 0}))

    return {"days": days, "data": all_days}
