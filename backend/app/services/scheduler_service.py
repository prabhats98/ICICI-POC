"""
Scheduler Service — APScheduler for periodic pipeline execution.
Existing pipeline scheduler (configurable interval) + 7-minute auto-scan.
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global scheduler instance
scheduler = AsyncIOScheduler()

# Pipeline enabled state (can be toggled via API)
_pipeline_enabled: bool = settings.pipeline_enabled


def is_pipeline_enabled() -> bool:
    """Check if the pipeline is currently enabled."""
    return _pipeline_enabled


def set_pipeline_enabled(enabled: bool) -> None:
    """Toggle the pipeline on or off."""
    global _pipeline_enabled
    _pipeline_enabled = enabled
    logger.info(f"Pipeline {'enabled' if enabled else 'disabled'}")


async def run_pipeline_job():
    """Scheduled job that triggers the agent pipeline with retry."""
    if not _pipeline_enabled:
        logger.info("Scheduler: Pipeline is disabled, skipping run")
        return

    from app.agents.graph import run_pipeline

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Scheduler: Starting pipeline run (attempt {attempt}/{max_retries})...")
            result = await run_pipeline(trigger_type="scheduler")
            status = result.get("status", "unknown")
            logger.info(f"Scheduler: Pipeline run completed with status: {status}")
            return
        except Exception as e:
            logger.error(f"Scheduler: Pipeline attempt {attempt} failed: {e}")
            if attempt < max_retries:
                backoff = 2 ** attempt * 10  # 20s, 40s, 80s
                logger.info(f"Scheduler: Retrying in {backoff}s...")
                await asyncio.sleep(backoff)
            else:
                logger.error("Scheduler: All retry attempts exhausted")


# ══════════════════════════════════════════
# 7-MINUTE AUTO-SCAN SCHEDULER
# ══════════════════════════════════════════
_auto_scan_running = False


async def run_auto_scan_job():
    """Every 7 minutes: check past 7 min logs, run pipeline, send RCA email if incidents found."""
    global _auto_scan_running
    if _auto_scan_running:
        logger.info("Auto-scan: Previous run still in progress, skipping")
        return
    if not _pipeline_enabled:
        logger.info("Auto-scan: Pipeline disabled, skipping")
        return

    _auto_scan_running = True
    scan_start = time.time()

    try:
        from app.agents.graph import run_pipeline

        # Calculate last 7 minutes
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=7)
        start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(f"Auto-scan: Checking logs from {start_str} to {end_str}")

        result = await run_pipeline(
            trigger_type="auto_scan_7min",
            start_date=start_str,
            end_date=end_str,
        )

        status = result.get("status", "unknown")
        summary = result.get("summary", {})
        total_incidents = summary.get("total_incidents", 0)
        p1 = summary.get("p1_count", 0)
        p2 = summary.get("p2_count", 0)
        p3 = summary.get("p3_count", 0)
        duration = round(time.time() - scan_start, 1)

        logger.info(
            f"Auto-scan completed in {duration}s: status={status}, "
            f"incidents={total_incidents} (P1:{p1} P2:{p2} P3:{p3})"
        )

        # If incidents found, send RCA notification email
        if total_incidents > 0:
            await _send_auto_scan_rca_email(summary, start_str, end_str, total_incidents, p1, p2, p3)

    except Exception as e:
        logger.error(f"Auto-scan failed: {e}")
    finally:
        _auto_scan_running = False


async def _send_auto_scan_rca_email(summary, start_str, end_str, total, p1, p2, p3):
    """Send RCA notification email with full incident details when auto-scan finds incidents."""
    try:
        from app.services.graph_email_service import graph_email_service

        now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

        # Query actual incident details from DB
        incident_blocks = ""
        try:
            from app.database import async_session as db_session
            from sqlalchemy import text
            async with db_session() as session:
                q = await session.execute(text(
                    "SELECT title, description, priority, category, source_service, "
                    "root_cause, root_cause_category, affected_component, "
                    "immediate_resolution, preventive_action, business_impact, "
                    "confidence_score, log_count "
                    "FROM incidents WHERE created_at >= :start AND created_at <= :end "
                    "ORDER BY priority, created_at DESC LIMIT 10"
                ), {"start": start_str, "end": end_str})
                incidents = q.fetchall()

                for inc in incidents:
                    title = inc[0] or "Unknown Incident"
                    desc = inc[1] or ""
                    prio = inc[2] or "P3"
                    category = inc[3] or ""
                    source = inc[4] or ""
                    root_cause = inc[5] or "Under analysis"
                    rca_cat = inc[6] or ""
                    component = inc[7] or ""
                    resolution = inc[8] or ""
                    preventive = inc[9] or ""
                    biz_impact = inc[10] or ""
                    confidence = inc[11] or 0
                    log_count = inc[12] or 0

                    sev_color = "#ef4444" if prio == "P1" else "#f59e0b" if prio == "P2" else "#64748b"
                    sev_bg = "#fef2f2" if prio == "P1" else "#fffbeb" if prio == "P2" else "#f8fafc"

                    # Build details sections
                    details_html = ""
                    if root_cause and root_cause != "Under analysis":
                        details_html += f"""
                        <div style="margin-bottom:8px;">
                            <div style="font-size:10px;font-weight:700;color:{sev_color};text-transform:uppercase;margin-bottom:2px;">Root Cause</div>
                            <div style="font-size:12px;color:#0f172a;line-height:1.5;">{root_cause[:500]}</div>
                        </div>"""
                    if biz_impact:
                        details_html += f"""
                        <div style="margin-bottom:8px;">
                            <div style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;margin-bottom:2px;">Business Impact</div>
                            <div style="font-size:12px;color:#334155;line-height:1.5;">{biz_impact[:300]}</div>
                        </div>"""
                    if resolution:
                        details_html += f"""
                        <div style="background:white;border-radius:6px;padding:8px 10px;border:1px solid #e2e8f0;margin-bottom:6px;">
                            <div style="font-size:10px;font-weight:700;color:#0369a1;text-transform:uppercase;margin-bottom:2px;">Immediate Resolution</div>
                            <div style="font-size:11px;color:#334155;line-height:1.5;">{resolution[:400]}</div>
                        </div>"""
                    if preventive:
                        details_html += f"""
                        <div style="background:white;border-radius:6px;padding:8px 10px;border:1px solid #e2e8f0;">
                            <div style="font-size:10px;font-weight:700;color:#166534;text-transform:uppercase;margin-bottom:2px;">Preventive Action</div>
                            <div style="font-size:11px;color:#334155;line-height:1.5;">{preventive[:400]}</div>
                        </div>"""

                    # Meta info
                    meta_parts = []
                    if source:
                        meta_parts.append(f"Service: {source}")
                    if component:
                        meta_parts.append(f"Component: {component}")
                    if rca_cat:
                        meta_parts.append(f"Category: {rca_cat}")
                    if confidence:
                        meta_parts.append(f"Confidence: {int(confidence * 100)}%")
                    if log_count:
                        meta_parts.append(f"Logs: {log_count}")
                    meta_str = " | ".join(meta_parts)

                    incident_blocks += f"""
                    <div style="background:{sev_bg};border:1px solid {sev_color}25;border-left:4px solid {sev_color};border-radius:8px;padding:14px 16px;margin-bottom:12px;">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                            <span style="background:{sev_color};color:white;padding:2px 10px;border-radius:4px;font-size:10px;font-weight:700;">{prio}</span>
                            <span style="font-size:14px;font-weight:800;color:#0f172a;">{title[:120]}</span>
                        </div>
                        <div style="font-size:11px;color:#94a3b8;margin-bottom:8px;">{meta_str}</div>
                        {f'<div style="font-size:12px;color:#475569;margin-bottom:10px;line-height:1.5;">{desc[:300]}</div>' if desc else ''}
                        {details_html}
                    </div>"""

        except Exception as db_err:
            logger.warning(f"Failed to get incident details for email: {db_err}")
            incident_blocks = f"""
            <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px;margin-bottom:12px;">
                <p style="margin:0;font-size:12px;color:#92400e;">
                    {total} incident(s) detected. Open the dashboard to view full details.
                </p>
            </div>"""

        # Priority summary
        priority_badges = ""
        if p1 > 0:
            priority_badges += f'<span style="display:inline-block;background:#fef2f2;border:1px solid #fecaca;border-radius:12px;padding:3px 12px;font-size:12px;color:#ef4444;font-weight:700;margin-right:6px;">P1: {p1}</span>'
        if p2 > 0:
            priority_badges += f'<span style="display:inline-block;background:#fffbeb;border:1px solid #fde68a;border-radius:12px;padding:3px 12px;font-size:12px;color:#d97706;font-weight:700;margin-right:6px;">P2: {p2}</span>'
        if p3 > 0:
            priority_badges += f'<span style="display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:3px 12px;font-size:12px;color:#64748b;font-weight:700;margin-right:6px;">P3: {p3}</span>'

        highest = "P1" if p1 > 0 else "P2" if p2 > 0 else "P3"
        header_color = "#dc2626" if p1 > 0 else "#d97706" if p2 > 0 else "#4f46e5"

        html_body = f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:700px;margin:0 auto;">
            <div style="background:linear-gradient(135deg,{header_color} 0%,#1e1b4b 100%);padding:18px 24px;border-radius:10px 10px 0 0;">
                <h1 style="margin:0;color:white;font-size:18px;">CloudGuard - Auto-Scan RCA Report</h1>
                <p style="margin:4px 0 0;color:#fecaca;font-size:12px;">7-minute automated incident detection with full root cause analysis</p>
            </div>
            <div style="background:#f8fafc;padding:18px 24px;border:1px solid #e2e8f0;border-radius:0 0 10px 10px;">

                <div style="background:#fef2f2;padding:12px 14px;border-radius:8px;margin-bottom:14px;border:1px solid #fecaca;">
                    <p style="margin:0;font-size:14px;color:#991b1b;font-weight:700;">
                        {total} incident(s) detected in the last 7 minutes
                    </p>
                    <p style="margin:4px 0 0;font-size:11px;color:#6b7280;">
                        Scan: {start_str} to {end_str} | Website: <strong>www.icicipruamc.com</strong> | Logs: {summary.get('total_preprocessed', 0)}
                    </p>
                    <div style="margin-top:6px;">{priority_badges}</div>
                </div>

                <div style="font-size:11px;font-weight:700;color:#475569;text-transform:uppercase;margin-bottom:10px;letter-spacing:0.5px;">Incident Details + Root Cause Analysis</div>

                {incident_blocks}

                <div style="padding:10px;background:#f0f9ff;border-radius:6px;border:1px solid #bae6fd;">
                    <p style="margin:0;font-size:11px;color:#0369a1;">
                        <a href="http://10.238.46.116" style="color:#0369a1;font-weight:700;">Open Dashboard</a> for full details |
                        Source: Azure Blob Storage + Log Analytics |
                        Auto-scan runs every 7 min | {now_str}
                    </p>
                </div>
            </div>
        </div>"""

        subject = f"[CloudGuard] {highest} Auto-Scan: {total} incident(s) + RCA - www.icicipruamc.com"
        sent = await graph_email_service.send_email(
            to_email="prabhat_singh@ext.icicipruamc.com",
            subject=subject,
            html_body=html_body,
        )
        if sent:
            logger.info(f"Auto-scan RCA email sent: {total} incidents (P1:{p1} P2:{p2} P3:{p3})")
        else:
            logger.warning("Auto-scan RCA email failed to send")
    except Exception as e:
        logger.error(f"Auto-scan RCA email error: {e}")


def start_scheduler():
    """Start the scheduler if enabled in config."""
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled in configuration")
        return

    # Existing manual/scheduled pipeline (keeps original interval)
    scheduler.add_job(
        run_pipeline_job,
        trigger=IntervalTrigger(hours=settings.scheduler_interval_hours),
        id="pipeline_scheduler",
        name=f"Pipeline Scheduler (every {settings.scheduler_interval_hours}h)",
        replace_existing=True,
        max_instances=1,
    )

    # NEW: 7-minute auto-scan for recent incidents
    scheduler.add_job(
        run_auto_scan_job,
        trigger=IntervalTrigger(minutes=7),
        id="auto_scan_7min",
        name="Auto-Scan (every 7 min - last 7 min logs)",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started: pipeline every {settings.scheduler_interval_hours}h + auto-scan every 7 min"
    )


def stop_scheduler():
    """Stop the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def pause_scheduler():
    """Pause the scheduled job."""
    job = scheduler.get_job("pipeline_scheduler")
    if job:
        job.pause()
        logger.info("Scheduler paused")


def resume_scheduler():
    """Resume the scheduled job."""
    job = scheduler.get_job("pipeline_scheduler")
    if job:
        job.resume()
        logger.info("Scheduler resumed")


def get_next_run_time():
    """Get the next scheduled run time."""
    job = scheduler.get_job("pipeline_scheduler")
    if job:
        return job.next_run_time
    return None


def get_scheduler_status() -> dict:
    """Full scheduler status for the API."""
    job = scheduler.get_job("pipeline_scheduler")
    auto_scan = scheduler.get_job("auto_scan_7min")
    return {
        "enabled": settings.scheduler_enabled,
        "pipeline_enabled": _pipeline_enabled,
        "scheduler_running": scheduler.running,
        "interval_hours": settings.scheduler_interval_hours,
        "next_run_at": str(job.next_run_time) if job and job.next_run_time else None,
        "job_state": str(job.next_run_time is not None) if job else "no_job",
        "auto_scan_enabled": True,
        "auto_scan_interval_min": 7,
        "auto_scan_next_run": str(auto_scan.next_run_time) if auto_scan and auto_scan.next_run_time else None,
    }
