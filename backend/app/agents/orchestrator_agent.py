"""
Agent 7: Orchestrator Agent

Coordinates all agent outputs, aggregates the pipeline summary,
determines which incidents need email notifications, and handles
WebSocket broadcasting for real-time dashboard updates.
"""

import logging
from typing import Any

from app.agents.state import PipelineState

logger = logging.getLogger(__name__)


async def orchestrator_agent_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Coordinate pipeline outputs and decide next steps.

    1. Aggregate final pipeline summary
    2. Determine which incidents need email notification
       - P1: Always send email
       - P2: Send email digest
       - P3: Dashboard only (no email)
    3. Prepare notification payload
    """
    p1 = state.get("p1_incidents", [])
    p2 = state.get("p2_incidents", [])
    p3 = state.get("p3_incidents", [])
    resolutions = state.get("resolutions", [])

    logger.info(
        f"Agent 7 [Orchestrator]: Coordinating — "
        f"P1={len(p1)}, P2={len(p2)}, P3={len(p3)}, Resolutions={len(resolutions)}"
    )

    # Build resolution lookup
    resolution_map = {}
    for res in resolutions:
        if res.get("incident_id"):
            resolution_map[res["incident_id"]] = res

    # Determine notifications
    notifications_to_send = []

    # P1 incidents: always send individual emails
    for incident in p1:
        resolution = resolution_map.get(incident["id"], {})
        notifications_to_send.append({
            "incident_id": incident["id"],
            "title": incident["title"],
            "priority": "P1",
            "description": incident.get("description", ""),
            "category": incident.get("category", ""),
            "affected_service": incident.get("affected_service", ""),
            "solution": resolution.get("solution", "Resolution pending"),
            "send_email": True,
        })

    # P2 incidents: send email digest
    for incident in p2:
        resolution = resolution_map.get(incident["id"], {})
        notifications_to_send.append({
            "incident_id": incident["id"],
            "title": incident["title"],
            "priority": "P2",
            "description": incident.get("description", ""),
            "category": incident.get("category", ""),
            "affected_service": incident.get("affected_service", ""),
            "solution": resolution.get("solution", "Resolution pending"),
            "send_email": True,
        })

    # P3 incidents: dashboard only
    for incident in p3:
        resolution = resolution_map.get(incident["id"], {})
        notifications_to_send.append({
            "incident_id": incident["id"],
            "title": incident["title"],
            "priority": "P3",
            "description": incident.get("description", ""),
            "solution": resolution.get("solution", ""),
            "send_email": False,
        })

    # Build summary
    summary = {
        "total_collected": state.get("total_collected", 0),
        "per_source": state.get("per_source", {}),
        "total_preprocessed": state.get("total_preprocessed", 0),
        "duplicates_removed": state.get("duplicates_removed", 0),
        "logs_analyzed": state.get("logs_analyzed", 0),
        "issues_found": len(state.get("issues_found", [])),
        "p1_count": len(p1),
        "p2_count": len(p2),
        "p3_count": len(p3),
        "total_incidents": len(p1) + len(p2) + len(p3),
        "resolutions_generated": len([r for r in resolutions if not r.get("error")]),
        "emails_to_send": len([n for n in notifications_to_send if n.get("send_email")]),
        "level_counts": state.get("level_counts", {}),
        "category_counts": state.get("category_counts", {}),
    }

    logger.info(
        f"Agent 7 [Orchestrator]: Summary — "
        f"{summary['total_incidents']} incidents, "
        f"{summary['resolutions_generated']} resolutions, "
        f"{summary['emails_to_send']} emails to send"
    )

    return {
        "summary": summary,
        "notifications_to_send": notifications_to_send,
        "current_agent": "orchestrator_agent",
    }
