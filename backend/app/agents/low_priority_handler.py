"""
Agent 4c: Low Priority Handler (Solution Architect) - Generates solutions
and sends informational email notifications for low-priority incidents.
"""

import logging
from typing import Any
from datetime import datetime

from sqlalchemy import update

from app.database import async_session
from app.models.incident import Incident, IncidentStatus
from app.agents.state import PipelineState
from app.services.gemini_service import gemini_service
from app.services.email_service import email_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def low_priority_handler_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Handle LOW priority incidents.
    
    For each low-priority incident:
    1. Generate a solution using Gemini
    2. Generate an informational email body
    3. Send email to the production manager
    4. Update the incident record in DB
    """
    incidents = state.get("low_priority_incidents", [])
    logger.info(f"Agent 4c [Solution Architect - Low]: Processing {len(incidents)} low-priority items...")

    if not incidents:
        return {
            "low_priority_logged": 0,
            "low_priority_solutions": [],
            "low_emails_sent": [],
            "current_agent": "low_priority_handler",
        }

    solutions = []
    emails_sent = []

    for incident in incidents:
        try:
            # Step 1: Generate solution using Gemini
            solution_text = await gemini_service.generate_solution(incident)

            # Step 2: Generate email content
            email_content = await gemini_service.generate_email_body(incident, solution_text)

            # Step 3: Send informational email
            email_sent = await email_service.send_alert_email(
                subject=email_content.get("subject", f"[LOW] {incident.get('title', 'Info')}"),
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
                            status=IncidentStatus.IN_PROGRESS,
                            email_sent=email_sent,
                            email_sent_at=datetime.utcnow() if email_sent else None,
                            email_recipient=settings.smtp_to_email,
                        )
                    )
                    await session.commit()
            except Exception as db_err:
                logger.warning(f"DB update failed for incident {incident.get('id')}: {db_err}")

            solutions.append({
                "incident_id": incident.get("id"),
                "title": incident.get("title"),
                "solution": solution_text,
                "email_sent": email_sent,
            })

            if email_sent:
                emails_sent.append(incident.get("id"))

            logger.info(
                f"Agent 4c [Solution Architect - Low]: Processed '{incident.get('title', 'Unknown')}' - "
                f"Email {'sent' if email_sent else 'failed'}"
            )

        except Exception as e:
            logger.error(f"Agent 4c failed for incident {incident.get('title')}: {e}")
            solutions.append({
                "incident_id": incident.get("id"),
                "title": incident.get("title"),
                "error": str(e),
            })

    return {
        "low_priority_logged": len(incidents),
        "low_priority_solutions": solutions,
        "low_emails_sent": emails_sent,
        "current_agent": "low_priority_handler",
    }
