"""
Agent 4: Priority Agent

Classifies detected issues into P1 / P2 / P3 and creates Incident records.
"""

import uuid
import logging
from typing import Any
from datetime import datetime

from app.database import async_session
from app.models.incident import Incident, PriorityLevel, IncidentStatus
from app.agents.state import PipelineState
from app.services.gemini_service import gemini_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def priority_agent_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Assign P1/P2/P3 priority and create Incident records.
    """
    issues = state.get("issues_found", [])
    run_id = state.get("run_id", "")
    logger.info(f"Agent 4 [Priority]: Classifying {len(issues)} issues...")

    if not issues:
        logger.info("Agent 4 [Priority]: No issues to classify")
        return {
            "classified_issues": [],
            "p1_incidents": [],
            "p2_incidents": [],
            "p3_incidents": [],
            "current_agent": "priority_agent",
        }

    try:
        classified = await gemini_service.assign_priority(issues)

        p1, p2, p3 = [], [], []

        async with async_session() as session:
            for item in classified:
                priority_str = item.get("priority", "P3").upper()
                priority_map = {"P1": PriorityLevel.P1, "P2": PriorityLevel.P2, "P3": PriorityLevel.P3}
                priority = priority_map.get(priority_str, PriorityLevel.P3)

                incident = Incident(
                    id=str(uuid.uuid4()),
                    title=item.get("original_title", "Unknown Issue"),
                    description=item.get("enriched_description", item.get("description", "")),
                    priority=priority,
                    category=item.get("category", "Uncategorized"),
                    source_service=item.get("affected_service", "Unknown"),
                    status=IncidentStatus.OPEN,
                    ai_analysis=item.get("justification", ""),
                    ai_model_used=settings.gemini_model,
                    agent_run_id=run_id or None,
                )
                session.add(incident)

                incident_dict = {
                    "id": str(incident.id),
                    "title": incident.title,
                    "description": incident.description,
                    "priority": priority_str,
                    "category": incident.category,
                    "severity": item.get("severity", 5),
                    "justification": item.get("justification", ""),
                    "affected_service": item.get("affected_service", "Unknown"),
                    "root_cause": item.get("root_cause", "Unknown"),
                    "incident_type": item.get("incident_type", ""),
                }

                if priority == PriorityLevel.P1:
                    p1.append(incident_dict)
                elif priority == PriorityLevel.P2:
                    p2.append(incident_dict)
                else:
                    p3.append(incident_dict)

            await session.commit()

        logger.info(f"Agent 4 [Priority]: P1={len(p1)}, P2={len(p2)}, P3={len(p3)}")

        return {
            "classified_issues": classified,
            "p1_incidents": p1,
            "p2_incidents": p2,
            "p3_incidents": p3,
            "current_agent": "priority_agent",
        }

    except Exception as e:
        logger.error(f"Agent 4 [Priority] failed: {e}")
        return {
            "classified_issues": [],
            "p1_incidents": [],
            "p2_incidents": [],
            "p3_incidents": [],
            "errors": [f"Priority classification failed: {str(e)}"],
            "current_agent": "priority_agent",
        }
