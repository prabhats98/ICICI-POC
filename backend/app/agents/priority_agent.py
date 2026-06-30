"""
Agent 4: Priority Agent

Classifies detected issues into P1 / P2 / P3 and creates Incident records.
Consumes RCA results to enrich incidents with root cause data.
"""

import uuid
import logging
from typing import Any
from datetime import datetime

from app.database import async_session
from app.models.incident import Incident, PriorityLevel, IncidentStatus
from app.models.recommendation import Recommendation
from app.agents.state import PipelineState
from app.services.gemini_service import gemini_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _merge_rca_into_issues(issues: list, rca_results: list) -> list:
    """Merge RCA data into issues for priority classification."""
    # Build a lookup from issue title to RCA
    rca_lookup = {}
    for rca in rca_results:
        issue = rca.get("issue", {})
        key = issue.get("title", "")
        if key:
            rca_lookup[key] = rca

    merged = []
    for issue in issues:
        title = issue.get("title", "")
        rca = rca_lookup.get(title, {})
        enriched = {**issue}
        if rca:
            enriched["root_cause"] = rca.get("root_cause", "")
            enriched["root_cause_category"] = rca.get("root_cause_category", "")
            enriched["confidence_score"] = rca.get("confidence_score", 0)
            enriched["affected_component"] = rca.get("affected_component", "")
            enriched["immediate_resolution"] = rca.get("immediate_resolution", "")
            enriched["preventive_action"] = rca.get("preventive_action", "")
            enriched["business_impact"] = rca.get("business_impact", "")
            enriched["owner_team"] = rca.get("owner_team", "")
            enriched["est_resolution_min"] = rca.get("est_resolution_min", 30)
            enriched["incident_group_id"] = rca.get("incident_group_id")
            enriched["rca_id"] = rca.get("rca_id")
        merged.append(enriched)
    return merged


async def priority_agent_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Assign P1/P2/P3 priority and create Incident records.
    Merges RCA data from the upstream RCA Agent.
    """
    issues = state.get("issues_found", [])
    rca_results = state.get("rca_results", [])
    run_id = state.get("run_id", "")
    logger.info(f"Agent 4 [Priority]: Classifying {len(issues)} issues ({len(rca_results)} RCA results)...")

    if not issues:
        logger.info("Agent 4 [Priority]: No issues to classify")
        return {
            "classified_issues": [],
            "p1_incidents": [],
            "p2_incidents": [],
            "p3_incidents": [],
            "current_agent": "priority_agent",
        }

    # Merge RCA data into issues
    enriched_issues = _merge_rca_into_issues(issues, rca_results)

    def _safe_str(val, default=""):
        """Convert any value to a safe string for SQLite."""
        if val is None:
            return default
        if isinstance(val, list):
            return "; ".join(str(v) for v in val)
        if isinstance(val, dict):
            return str(val)
        return str(val)

    try:
        classified = await gemini_service.assign_priority(enriched_issues)

        p1, p2, p3 = [], [], []

        async with async_session() as session:
            for item in classified:
                priority_str = item.get("priority", "P3").upper()
                priority_map = {"P1": PriorityLevel.P1, "P2": PriorityLevel.P2, "P3": PriorityLevel.P3}
                priority = priority_map.get(priority_str, PriorityLevel.P3)

                # Find matching enriched issue for RCA fields
                orig_title = item.get("original_title", "Unknown Issue")
                rca_data = next((e for e in enriched_issues if e.get("title") == orig_title), {})

                incident = Incident(
                    id=str(uuid.uuid4()),
                    title=_safe_str(orig_title, "Unknown Issue"),
                    description=_safe_str(item.get("enriched_description", item.get("description", "")), "No description"),
                    priority=priority,
                    category=_safe_str(item.get("category", "Uncategorized")),
                    source_service=_safe_str(rca_data.get("source_service") or rca_data.get("affected_service") or item.get("affected_service", "Azure")),
                    status=IncidentStatus.OPEN,
                    ai_analysis=_safe_str(item.get("justification", "")),
                    ai_model_used=settings.gemini_model,
                    agent_run_id=run_id or None,
                    # RCA fields (denormalized from RCA Agent)
                    incident_group_id=rca_data.get("incident_group_id"),
                    root_cause=_safe_str(rca_data.get("root_cause", item.get("root_cause", ""))),
                    root_cause_category=_safe_str(rca_data.get("root_cause_category", "")),
                    confidence_score=rca_data.get("confidence_score"),
                    affected_component=_safe_str(rca_data.get("affected_component", "")),
                    # Recommendation fields
                    immediate_resolution=_safe_str(rca_data.get("immediate_resolution", "")),
                    preventive_action=_safe_str(rca_data.get("preventive_action", "")),
                    business_impact=_safe_str(rca_data.get("business_impact", "")),
                    estimated_resolution_minutes=rca_data.get("est_resolution_min"),
                    owner_team=_safe_str(rca_data.get("owner_team", "")),
                )
                session.add(incident)

                # Also persist a Recommendation record
                if rca_data.get("immediate_resolution"):
                    rec = Recommendation(
                        id=str(uuid.uuid4()),
                        incident_group_id=_safe_str(rca_data.get("incident_group_id", "")),
                        incident_id=str(incident.id),
                        immediate_resolution=_safe_str(rca_data.get("immediate_resolution", "")),
                        preventive_action=_safe_str(rca_data.get("preventive_action", "")),
                        priority=priority_str,
                        business_impact=_safe_str(rca_data.get("business_impact", "")),
                        estimated_resolution_minutes=rca_data.get("est_resolution_min"),
                        owner_team=_safe_str(rca_data.get("owner_team", "")),
                        generation_method="rule_based",
                        agent_run_id=run_id,
                    )
                    session.add(rec)

                incident_dict = {
                    "id": str(incident.id),
                    "title": incident.title,
                    "description": incident.description,
                    "priority": priority_str,
                    "category": incident.category,
                    "severity": item.get("severity", 5),
                    "justification": item.get("justification", ""),
                    "affected_service": item.get("affected_service", "Unknown"),
                    "root_cause": incident.root_cause or item.get("root_cause", "Unknown"),
                    "root_cause_category": incident.root_cause_category or "",
                    "confidence_score": incident.confidence_score,
                    "affected_component": incident.affected_component or "",
                    "immediate_resolution": incident.immediate_resolution or "",
                    "preventive_action": incident.preventive_action or "",
                    "business_impact": incident.business_impact or "",
                    "owner_team": incident.owner_team or "",
                    "incident_type": item.get("incident_type", ""),
                    "sample_logs": item.get("sample_logs", []),
                    "sample_endpoint": item.get("sample_endpoint", ""),
                    "affected_urls": item.get("affected_urls", []),
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


