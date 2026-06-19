"""
Agent 4b: Medium Priority Handler - Generates automated solutions
for medium-priority incidents without sending emails.
"""

import logging
from typing import Any

from sqlalchemy import update

from app.database import async_session
from app.models.incident import Incident, IncidentStatus
from app.agents.state import PipelineState
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


async def medium_priority_handler_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Handle MEDIUM priority incidents.
    
    For each medium-priority incident:
    1. Route to solution-finder sub-agent (Gemini)
    2. Generate a solution on-the-go
    3. Store solution in DB (visible in dashboard, no email)
    """
    incidents = state.get("medium_priority_incidents", [])
    logger.info(f"Agent 4b [Medium Priority]: Processing {len(incidents)} incidents...")

    if not incidents:
        return {
            "medium_priority_solutions": [],
            "current_agent": "medium_priority_handler",
        }

    solutions = []

    for incident in incidents:
        try:
            # Generate solution using Gemini
            solution_text = await gemini_service.generate_solution(incident)

            # Update incident in DB with solution
            try:
                async with async_session() as session:
                    await session.execute(
                        update(Incident)
                        .where(Incident.id == incident["id"])
                        .values(
                            ai_solution=solution_text,
                            status=IncidentStatus.IN_PROGRESS,
                        )
                    )
                    await session.commit()
            except Exception as db_err:
                logger.warning(f"DB update failed for incident {incident['id']}: {db_err}")

            solutions.append({
                "incident_id": incident["id"],
                "title": incident["title"],
                "solution": solution_text,
            })

            logger.info(
                f"Agent 4b [Medium Priority]: Solution generated for '{incident['title']}'"
            )

        except Exception as e:
            logger.error(f"Agent 4b failed for incident {incident.get('title')}: {e}")
            solutions.append({
                "incident_id": incident.get("id"),
                "title": incident.get("title"),
                "error": str(e),
            })

    return {
        "medium_priority_solutions": solutions,
        "current_agent": "medium_priority_handler",
    }
