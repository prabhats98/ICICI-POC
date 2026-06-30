"""
Agent 8: Notification Agent

Sends email alerts to relevant team members based on priority.
P1 → immediate email, P2 → email digest, P3 → dashboard only.

Performance: Generates email bodies concurrently, then sends emails
in batches with rate-limit pauses only between batches (not after each email).
"""

import logging
import asyncio
from typing import Any
from datetime import datetime

from sqlalchemy import update

from app.database import async_session
from app.models.incident import Incident
from app.agents.state import PipelineState
from app.services.email_service import email_service
from app.services.gemini_service import gemini_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# How many emails to send in each batch before pausing for rate limits
BATCH_SIZE = 5
# Seconds to wait between batches
BATCH_PAUSE_SECONDS = 2
# Max concurrent Gemini calls for email body generation
MAX_CONCURRENT_GEMINI = 5


async def _generate_email_content(notification: dict) -> dict:
    """Generate email subject + body for a single notification using Gemini."""
    try:
        email_content = await gemini_service.generate_email_body(
            notification,
            notification.get("solution", "Resolution in progress"),
        )
        return {
            "notification": notification,
            "subject": email_content.get(
                "subject",
                f"[{notification['priority']}] {notification['title']}"
            ),
            "html_body": email_content.get(
                "body",
                f"<p>{notification.get('description', '')}</p>"
            ),
            "error": None,
        }
    except Exception as e:
        logger.warning(f"Email body generation failed for {notification.get('title', '?')}: {e}")
        # Fallback: use a simple template
        time_info = ""
        if notification.get('incident_time_range'):
            time_info = f"<p><strong>Incident Date/Time:</strong> {notification.get('incident_time_range')}</p>"
        return {
            "notification": notification,
            "subject": f"[{notification.get('priority', '?')}] {notification.get('title', 'Incident Alert')}",
            "html_body": (
                f"<h2>{notification.get('title', 'Incident Alert')}</h2>"
                f"<p><strong>Priority:</strong> {notification.get('priority', '?')}</p>"
                f"<p><strong>Service:</strong> {notification.get('source_service', '?')}</p>"
                f"{time_info}"
                f"<p>{notification.get('description', '')}</p>"
                f"<p><strong>Recommended Fix:</strong> {notification.get('solution', 'N/A')}</p>"
            ),
            "error": None,
        }


async def _send_single_email(prepared: dict) -> dict:
    """Send a single prepared email and update the DB."""
    notification = prepared["notification"]
    incident_id = notification["incident_id"]
    recipient = (
        settings.smtp_to_email
        or 'prabhat.s@krelixir.com'
    )

    try:
        sent = await email_service.send_alert_email(
            subject=prepared["subject"],
            html_body=prepared["html_body"],
        )

        # Update incident record in DB
        try:
            async with async_session() as session:
                await session.execute(
                    update(Incident)
                    .where(Incident.id == incident_id)
                    .values(
                        email_sent=sent,
                        email_sent_at=datetime.utcnow() if sent else None,
                        email_recipient=recipient,
                    )
                )
                await session.commit()
        except Exception as db_err:
            logger.warning(f"DB update failed for notification {incident_id}: {db_err}")

        if sent:
            logger.info(
                f"Agent 8 [Notification]: ✅ Email sent for "
                f"[{notification['priority']}] {notification['title'][:50]}"
            )
        else:
            logger.warning(f"Agent 8 [Notification]: ❌ Email failed for {incident_id}")

        return {"incident_id": incident_id, "sent": sent}

    except Exception as e:
        logger.error(f"Agent 8 [Notification] send failed for {notification.get('title')}: {e}")
        return {"incident_id": incident_id, "sent": False}


async def notification_agent_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Send notifications for incidents.

    Performance optimizations:
    1. Generate all email bodies concurrently (bounded by semaphore)
    2. Send emails in batches with rate-limit pauses only between batches
    3. No sleep after the final batch
    """
    notifications = state.get("notifications_to_send", [])
    email_notifications = [n for n in notifications if n.get("send_email")]

    logger.info(
        f"Agent 8 [Notification]: Processing {len(notifications)} notifications "
        f"({len(email_notifications)} emails to send)"
    )

    if not email_notifications:
        return {
            "emails_sent": [],
            "email_failures": [],
            "current_agent": "notification_agent",
        }

    # ── Handle "Healthy" notifications (no incidents found) ──
    healthy_notifs = [n for n in email_notifications if n.get("is_healthy")]
    incident_notifs = [n for n in email_notifications if not n.get("is_healthy")]

    healthy_sent = []
    for healthy in healthy_notifs:
        time_range = healthy.get("incident_time_range", "")
        level_counts = healthy.get("level_counts", {})
        logs_analyzed = healthy.get("logs_analyzed", 0)
        desc = healthy.get("description", "")

        level_rows = ""
        for lvl, cnt in level_counts.items():
            color = {"ERROR": "#ef4444", "CRITICAL": "#dc2626", "WARNING": "#f59e0b", "INFO": "#10b981"}.get(lvl, "#64748b")
            level_rows += f'<tr><td style="padding:6px 12px;color:{color};font-weight:700">{lvl}</td><td style="padding:6px 12px">{cnt}</td></tr>'

        html_body = f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0">
          <div style="background:linear-gradient(135deg,#10b981,#059669);padding:28px 32px;text-align:center">
            <div style="font-size:36px;margin-bottom:8px">✅</div>
            <h1 style="color:#fff;font-size:22px;margin:0;font-weight:800">All Systems Healthy</h1>
            <p style="color:rgba(255,255,255,0.85);font-size:13px;margin:6px 0 0">CloudGuard AI Pipeline — Health Report</p>
          </div>
          <div style="padding:24px 32px">
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:16px;margin-bottom:20px">
              <p style="color:#166534;font-size:14px;font-weight:600;margin:0 0 8px">🎯 No incidents detected</p>
              <p style="color:#15803d;font-size:13px;margin:0;line-height:1.5">{desc}</p>
            </div>
            {"<p style='font-size:12px;color:#64748b;margin-bottom:12px'><strong>Time Range:</strong> " + time_range + "</p>" if time_range else ""}
            <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:16px">
              <tr style="background:#f8fafc"><th style="text-align:left;padding:8px 12px;color:#334155">Log Level</th><th style="text-align:left;padding:8px 12px;color:#334155">Count</th></tr>
              {level_rows if level_rows else '<tr><td style="padding:6px 12px" colspan="2">No logs in this time range</td></tr>'}
              <tr style="border-top:1px solid #e2e8f0"><td style="padding:8px 12px;font-weight:700;color:#0f172a">Total Analyzed</td><td style="padding:8px 12px;font-weight:700">{logs_analyzed}</td></tr>
            </table>
            <p style="font-size:11px;color:#94a3b8;text-align:center;margin-top:20px">CloudGuard by KR Elixir Technology — Automated Health Report</p>
          </div>
        </div>
        """

        try:
            sent = await email_service.send_alert_email(
                subject=f"✅ CloudGuard Health Report — All Systems Healthy ({time_range})" if time_range else "✅ CloudGuard — All Systems Healthy",
                html_body=html_body,
            )
            if sent:
                logger.info("Agent 8 [Notification]: ✅ Healthy status email sent")
                healthy_sent.append("__healthy__")
            else:
                logger.warning("Agent 8 [Notification]: ❌ Healthy status email failed")
        except Exception as e:
            logger.error(f"Agent 8 [Notification]: Healthy email error: {e}")

    # If only healthy notifications, return early
    if not incident_notifs:
        return {
            "emails_sent": healthy_sent,
            "email_failures": [],
            "current_agent": "notification_agent",
        }

    email_notifications = incident_notifs

    # ── Step 1: Generate all email bodies concurrently ──
    logger.info(f"Agent 8 [Notification]: Generating {len(email_notifications)} email bodies concurrently...")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_GEMINI)

    async def generate_with_limit(notif):
        async with semaphore:
            return await _generate_email_content(notif)

    prepared_emails = await asyncio.gather(
        *[generate_with_limit(n) for n in email_notifications]
    )
    logger.info(f"Agent 8 [Notification]: All email bodies generated")

    # ── Step 2: Send emails in batches ──
    emails_sent = []
    email_failures = []
    total_batches = (len(prepared_emails) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(total_batches):
        batch_start = batch_idx * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(prepared_emails))
        batch = prepared_emails[batch_start:batch_end]

        logger.info(
            f"Agent 8 [Notification]: Sending batch {batch_idx + 1}/{total_batches} "
            f"({len(batch)} emails)"
        )

        # Send all emails in this batch concurrently
        results = await asyncio.gather(
            *[_send_single_email(p) for p in batch]
        )

        for result in results:
            if result["sent"]:
                emails_sent.append(result["incident_id"])
            else:
                email_failures.append(result["incident_id"])

        # Pause between batches (NOT after the last batch)
        if batch_idx < total_batches - 1:
            logger.info(
                f"Agent 8 [Notification]: Rate-limit pause ({BATCH_PAUSE_SECONDS}s) "
                f"before next batch..."
            )
            await asyncio.sleep(BATCH_PAUSE_SECONDS)

    logger.info(
        f"Agent 8 [Notification]: Done — {len(emails_sent)} sent, {len(email_failures)} failed"
    )

    return {
        "emails_sent": emails_sent,
        "email_failures": email_failures,
        "current_agent": "notification_agent",
    }
