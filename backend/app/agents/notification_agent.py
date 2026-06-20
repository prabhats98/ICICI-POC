"""
Agent 8: Notification Agent

Sends email alerts to relevant team members based on priority.
P1 → immediate email, P2 → email digest, P3 → dashboard only.
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


async def notification_agent_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Send notifications for incidents.

    Uses the configured notification channel (SMTP or Azure Communication Services).
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

    emails_sent = []
    email_failures = []

    for notification in email_notifications:
        try:
            # Generate email content
            email_content = await gemini_service.generate_email_body(
                notification,
                notification.get("solution", "Resolution in progress"),
            )

            subject = email_content.get(
                "subject",
                f"[{notification['priority']}] {notification['title']}"
            )
            html_body = email_content.get("body", f"<p>{notification.get('description', '')}</p>")

            # Send email
            sent = await email_service.send_alert_email(
                subject=subject,
                html_body=html_body,
            )

            incident_id = notification["incident_id"]
            recipient = getattr(settings, 'azure_communication_email_to', None) or settings.smtp_to_email or 'prabhat.s@krelixir.com'

            # Update incident record
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
                emails_sent.append(incident_id)
                logger.info(f"Agent 8 [Notification]: Email sent for [{notification['priority']}] {notification['title'][:50]}")
            else:
                email_failures.append(incident_id)
                logger.warning(f"Agent 8 [Notification]: Email failed for {incident_id}")

            # Respect ACS free-tier rate limit: 1 email / 3 seconds
            await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"Agent 8 [Notification] failed for {notification.get('title')}: {e}")
            email_failures.append(notification.get("incident_id", "unknown"))

    logger.info(
        f"Agent 8 [Notification]: {len(emails_sent)} sent, {len(email_failures)} failed"
    )

    return {
        "emails_sent": emails_sent,
        "email_failures": email_failures,
        "current_agent": "notification_agent",
    }
