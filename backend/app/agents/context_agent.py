"""
Agent 5: Context Agent

Fetches similar historical incidents and known fixes from PostgreSQL
to enrich the current incidents with context for the Resolution Agent.
"""

import logging
from typing import Any

from sqlalchemy import select, and_, or_

from app.database import async_session
from app.models.incident import Incident, IncidentStatus
from app.agents.state import PipelineState

logger = logging.getLogger(__name__)


async def context_agent_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Enrich incidents with historical context.

    For each incident from the Priority Agent:
    1. Query past incidents with same category or similar title
    2. Find resolved incidents and extract their solutions
    3. Return enriched incidents with historical matches
    """
    all_incidents = (
        state.get("p1_incidents", [])
        + state.get("p2_incidents", [])
        + state.get("p3_incidents", [])
    )

    logger.info(f"Agent 5 [Context]: Looking up history for {len(all_incidents)} incidents...")

    if not all_incidents:
        return {
            "context_enriched_incidents": [],
            "current_agent": "context_agent",
        }

    enriched = []

    try:
        async with async_session() as session:
            for incident in all_incidents:
                category = incident.get("category", "")
                title = incident.get("title", "")
                incident_id = incident.get("id", "")

                # Find past resolved incidents with same category or similar title
                conditions = []
                if category:
                    conditions.append(Incident.category == category)
                if title and len(title) > 5:
                    # Simple LIKE match on title keywords
                    keywords = title.split()[:3]
                    for kw in keywords:
                        if len(kw) > 3:
                            conditions.append(Incident.title.ilike(f"%{kw}%"))

                if not conditions:
                    enriched.append({**incident, "historical_matches": [], "historical_match_count": 0})
                    continue

                query = (
                    select(Incident)
                    .where(
                        and_(
                            Incident.id != incident_id,
                            Incident.status.in_([IncidentStatus.RESOLVED, IncidentStatus.CLOSED]),
                            or_(*conditions),
                        )
                    )
                    .order_by(Incident.created_at.desc())
                    .limit(5)
                )

                result = await session.execute(query)
                past_incidents = result.scalars().all()

                historical_matches = []
                for past in past_incidents:
                    historical_matches.append({
                        "id": str(past.id),
                        "title": past.title,
                        "category": past.category,
                        "priority": past.priority.value if past.priority else "Unknown",
                        "solution": past.ai_solution,
                        "resolved_at": str(past.resolved_at) if past.resolved_at else None,
                    })

                enriched.append({
                    **incident,
                    "historical_matches": historical_matches,
                    "historical_match_count": len(historical_matches),
                })

                if historical_matches:
                    logger.info(
                        f"Agent 5 [Context]: Found {len(historical_matches)} matches for '{title[:50]}'"
                    )

        logger.info(f"Agent 5 [Context]: Enriched {len(enriched)} incidents with historical context")

        return {
            "context_enriched_incidents": enriched,
            "current_agent": "context_agent",
        }

    except Exception as e:
        logger.error(f"Agent 5 [Context] failed: {e}")
        # On failure, pass incidents through without context
        return {
            "context_enriched_incidents": [
                {**inc, "historical_matches": [], "historical_match_count": 0}
                for inc in all_incidents
            ],
            "errors": [f"Context lookup failed: {str(e)}"],
            "current_agent": "context_agent",
        }
