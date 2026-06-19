"""
Agent 4a: High Priority Handler - Generates solutions and sends alert emails
for critical incidents to the production manager.
"""

import logging
from typing import Any
from datetime import datetime

from sqlalchemy import update

from app.database import async_session
from app.models.incident import Incident
from app.agents.state import PipelineState
from app.services.gemini_service import gemini_service
from app.services.email_service import email_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def high_priority_handler_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Handle HIGH priority incidents.
    
    For each high-priority incident:
    1. Generate a detailed solution using Gemini
    2. Generate a professional alert email
    3. Send email to the production manager
    4. Update the incident record in DB
    """
    incidents = state.get("high_priority_incidents", [])
    logger.info(f"Agent 4a [High Priority]: Processing {len(incidents)} critical incidents...")

    if not incidents:
        return {
            "high_priority_solutions": [],
            "emails_sent": [],
            "current_agent": "high_priority_handler",
        }

    solutions = []
    emails_sent = []

    for incident in incidents:
        try:
            # Step 1: Generate detailed solution
            solution_text = await gemini_service.generate_solution(incident)

            # Step 2: Generate email content
            email_content = await gemini_service.generate_email_body(incident, solution_text)

            # Step 3: Send email to production manager
            email_sent = await email_service.send_alert_email(
                subject=email_content.get("subject", f"[CRITICAL] {incident['title']}"),
                html_body=email_content.get("body", solution_text),
            )

            # Step 4: Update incident in DB
            try:
                async with async_session() as session:
                    await session.execute(
                        update(Incident)
                        .where(Incident.id == incident["id"])
                        .values(
                            ai_solution=solution_text,
                            email_sent=email_sent,
                            email_sent_at=datetime.utcnow() if email_sent else None,
                            email_recipient=settings.smtp_to_email,
                        )
                    )
                    await session.commit()
            except Exception as db_err:
                logger.warning(f"DB update failed for incident {incident['id']}: {db_err}")

            solutions.append({
                "incident_id": incident["id"],
                "title": incident["title"],
                "solution": solution_text,
                "email_sent": email_sent,
            })

            if email_sent:
                emails_sent.append(incident["id"])

            logger.info(
                f"Agent 4a [High Priority]: Processed '{incident['title']}' - "
                f"Email {'sent' if email_sent else 'failed'}"
            )

        except Exception as e:
            logger.error(f"Agent 4a failed for incident {incident.get('title')}: {e}")
            solutions.append({
                "incident_id": incident.get("id"),
                "title": incident.get("title"),
                "error": str(e),
            })

    return {
        "high_priority_solutions": solutions,
        "emails_sent": emails_sent,
        "current_agent": "high_priority_handler",
    }
