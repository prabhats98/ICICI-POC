"""
Agent 6: Resolution Agent

Generates AI-powered resolution recommendations and runbooks for all incidents.
Uses historical context from the Context Agent for better suggestions.
"""

import logging
from typing import Any
from datetime import datetime

from sqlalchemy import update

from app.database import async_session
from app.models.incident import Incident, IncidentStatus
from app.agents.state import PipelineState
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


async def resolution_agent_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Generate resolution for each incident.

    For each incident:
    1. Use historical context from the Context Agent
    2. Call Gemini to generate a recommended fix / runbook
    3. Store the solution in the incidents table
    4. Mark incident as IN_PROGRESS
    """
    incidents = state.get("context_enriched_incidents", [])
    logger.info(f"Agent 6 [Resolution]: Generating fixes for {len(incidents)} incidents...")

    if not incidents:
        return {
            "resolutions": [],
            "current_agent": "resolution_agent",
        }

    resolutions = []

    for incident in incidents:
        try:
            historical = incident.get("historical_matches", [])

            # Generate resolution with historical context
            solution_text = await gemini_service.generate_resolution(incident, historical)

            # Update incident in DB
            try:
                async with async_session() as session:
                    update_values = {
                        "ai_solution": solution_text,
                        "resolution_runbook": solution_text,
                        "status": IncidentStatus.IN_PROGRESS,
                        "historical_match_count": len(historical),
                        "historical_match_ids": [h.get("id") for h in historical] if historical else None,
                    }
                    await session.execute(
                        update(Incident)
                        .where(Incident.id == incident["id"])
                        .values(**update_values)
                    )
                    await session.commit()
            except Exception as db_err:
                logger.warning(f"DB update failed for incident {incident['id']}: {db_err}")

            resolutions.append({
                "incident_id": incident["id"],
                "title": incident["title"],
                "priority": incident.get("priority", "P3"),
                "solution": solution_text,
                "historical_context_used": len(historical),
            })

            logger.info(
                f"Agent 6 [Resolution]: Generated fix for '{incident['title'][:50]}' "
                f"(context: {len(historical)} past incidents)"
            )

        except Exception as e:
            logger.error(f"Agent 6 [Resolution] failed for '{incident.get('title')}': {e}")
            resolutions.append({
                "incident_id": incident.get("id"),
                "title": incident.get("title"),
                "priority": incident.get("priority", "P3"),
                "error": str(e),
            })

    logger.info(f"Agent 6 [Resolution]: Generated {len(resolutions)} resolutions")

    return {
        "resolutions": resolutions,
        "current_agent": "resolution_agent",
    }
