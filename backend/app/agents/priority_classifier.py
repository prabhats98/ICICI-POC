"""
Agent 3: Priority Classifier - Classifies detected issues into
HIGH, MEDIUM, and LOW priority using Gemini.
"""

import uuid
import logging
from typing import Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.incident import Incident, PriorityLevel, IncidentStatus
from app.agents.state import PipelineState
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


async def priority_classifier_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Classify issues by priority and create Incident records.
    
    - Receives issues_found from Agent 2
    - Uses Gemini to classify into HIGH, MEDIUM, LOW
    - Creates Incident records in the database
    - Routes to appropriate handler agents
    """
    issues = state.get("issues_found", [])
    run_id = state.get("run_id", "")
    logger.info(f"Agent 3 [Priority Classifier]: Classifying {len(issues)} issues...")

    if not issues:
        logger.info("Agent 3 [Priority Classifier]: No issues to classify")
        return {
            "classified_issues": [],
            "high_priority_incidents": [],
            "medium_priority_incidents": [],
            "low_priority_incidents": [],
            "current_agent": "priority_classifier",
        }

    try:
        # Use Gemini to classify priorities
        classified = await gemini_service.classify_priority(issues)

        # Separate by priority
        high = []
        medium = []
        low = []

        async with async_session() as session:
            for item in classified:
                priority_str = item.get("priority", "LOW").upper()
                priority = PriorityLevel(priority_str) if priority_str in ["HIGH", "MEDIUM", "LOW"] else PriorityLevel.LOW

                # Create Incident record in DB
                incident = Incident(
                    id=uuid.uuid4(),
                    title=item.get("original_title", "Unknown Issue"),
                    description=item.get("enriched_description", item.get("description", "")),
                    priority=priority,
                    category=item.get("category", "Uncategorized"),
                    status=IncidentStatus.OPEN,
                    ai_analysis=item.get("justification", ""),
                    ai_model_used="gemini-2.5-flash",
                    agent_run_id=run_id if run_id else None,
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
                }

                if priority == PriorityLevel.HIGH:
                    high.append(incident_dict)
                elif priority == PriorityLevel.MEDIUM:
                    medium.append(incident_dict)
                else:
                    low.append(incident_dict)

            await session.commit()

        logger.info(
            f"Agent 3 [Priority Classifier]: HIGH={len(high)}, "
            f"MEDIUM={len(medium)}, LOW={len(low)}"
        )

        return {
            "classified_issues": classified,
            "high_priority_incidents": high,
            "medium_priority_incidents": medium,
            "low_priority_incidents": low,
            "current_agent": "priority_classifier",
        }

    except Exception as e:
        logger.error(f"Agent 3 [Priority Classifier] failed: {e}")
        return {
            "classified_issues": [],
            "high_priority_incidents": [],
            "medium_priority_incidents": [],
            "low_priority_incidents": [],
            "errors": [f"Priority classification failed: {str(e)}"],
            "current_agent": "priority_classifier",
        }
