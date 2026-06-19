"""
Agent 4c: Low Priority Handler - Logs low-priority issues for monitoring.
No email or immediate solution required.
"""

import logging
from typing import Any

from app.agents.state import PipelineState

logger = logging.getLogger(__name__)


async def low_priority_handler_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Handle LOW priority incidents.
    
    - Simply logs the data for historical tracking
    - No email sent
    - No immediate solution generated
    - Incidents already stored in DB by Agent 3
    """
    incidents = state.get("low_priority_incidents", [])
    logger.info(f"Agent 4c [Low Priority]: Logging {len(incidents)} low-priority items...")

    for incident in incidents:
        logger.info(
            f"Agent 4c [Low Priority]: Logged '{incident.get('title', 'Unknown')}' "
            f"- Category: {incident.get('category', 'N/A')} "
            f"- Service: {incident.get('affected_service', 'N/A')}"
        )

    return {
        "low_priority_logged": len(incidents),
        "current_agent": "low_priority_handler",
    }
