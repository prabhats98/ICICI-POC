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


def _fallback_resolution(incident: dict, category: str) -> str:
    """Generate a template-based resolution when Gemini is unavailable."""
    resolutions = {
        "WAF Security": (
            "## WAF Security Incident Resolution\n\n"
            "### Immediate Actions:\n"
            "1. Review WAF logs in Azure Portal → Front Door → WAF Policies\n"
            "2. Verify blocked IPs against known threat intelligence feeds\n"
            "3. Check if legitimate traffic is being blocked (false positives)\n\n"
            "### Investigation:\n"
            "- Review the WAF rule that triggered the block (rule ID in logs)\n"
            "- Check if the traffic pattern indicates automated scanning/bot activity\n"
            "- Verify geo-restriction rules are correctly configured\n\n"
            "### Remediation:\n"
            "- If false positive: Add exclusion rule for the specific URI/parameter\n"
            "- If legitimate threat: Ensure WAF policy is in Prevention mode\n"
            "- Consider adding rate limiting for suspicious source IPs\n"
            "- Update IP allowlist/blocklist as needed"
        ),
        "Performance": (
            "## Performance Incident Resolution\n\n"
            "### Immediate Actions:\n"
            "1. Check Azure Front Door origin health in Azure Portal\n"
            "2. Monitor backend response times (App Service / App Gateway)\n"
            "3. Check for resource exhaustion (CPU, memory, connections)\n\n"
            "### Investigation:\n"
            "- Review origin response latency trends in the last 24 hours\n"
            "- Check if specific URIs/endpoints are causing slow responses\n"
            "- Verify CDN caching rules are optimal\n\n"
            "### Remediation:\n"
            "- Scale up/out backend resources if under load\n"
            "- Optimize caching policies for static assets\n"
            "- Consider connection pooling and keep-alive optimizations\n"
            "- Review and optimize slow database queries"
        ),
        "Availability": (
            "## Availability Incident Resolution\n\n"
            "### Immediate Actions:\n"
            "1. Verify backend service health (App Service, VM, containers)\n"
            "2. Check Azure Status page for regional outages\n"
            "3. Review recent deployments that may have caused failures\n\n"
            "### Investigation:\n"
            "- Analyze HTTP error codes (4xx vs 5xx patterns)\n"
            "- Check application logs for exceptions/stack traces\n"
            "- Verify SSL certificates are valid and not expired\n\n"
            "### Remediation:\n"
            "- If 502/503: Restart backend service, check health probes\n"
            "- If 500: Roll back recent deployment, fix application bugs\n"
            "- If 404: Verify routing rules and URL rewrites\n"
            "- Set up auto-scaling to handle traffic spikes"
        ),
        "Health": (
            "## Health Probe Failure Resolution\n\n"
            "### Immediate Actions:\n"
            "1. Check backend service status immediately\n"
            "2. Verify health probe endpoint returns 200 OK\n"
            "3. Check network connectivity between Front Door and origin\n\n"
            "### Remediation:\n"
            "- Ensure health probe path exists and returns 200\n"
            "- Verify NSG/firewall rules allow Front Door health probes\n"
            "- Check if backend is overloaded and failing health checks"
        ),
    }
    return resolutions.get(category, (
        f"## Incident Resolution for: {incident.get('title', 'Unknown')}\n\n"
        "### Actions:\n"
        "1. Review the incident details in the Azure Portal\n"
        "2. Check related service health dashboards\n"
        "3. Escalate to the appropriate team if unresolved within SLA"
    ))


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

    # Pre-generate all Gemini resolutions CONCURRENTLY
    import asyncio as _aio
    sem = _aio.Semaphore(3)  # Max 3 concurrent Gemini calls

    async def _gen_resolution(inc):
        async with sem:
            try:
                historical = inc.get("historical_matches", [])
                return inc["id"], await gemini_service.generate_resolution(inc, historical), None
            except Exception as e:
                logger.warning(f"Gemini resolution failed for {inc.get('id', '?')}: {e}")
                return inc["id"], None, e

    # Fire all Gemini calls at once
    gen_tasks = [_gen_resolution(inc) for inc in incidents]
    gen_results = await _aio.gather(*gen_tasks)

    # Build a lookup: incident_id → solution text
    solution_map = {}
    for inc_id, sol, err in gen_results:
        if sol:
            solution_map[inc_id] = sol

    for incident in incidents:
        try:
            historical = incident.get("historical_matches", [])

            # Use pre-generated solution or fallback
            solution_text = solution_map.get(incident["id"])
            if not solution_text:
                category = incident.get("category", "General")
                solution_text = _fallback_resolution(incident, category)

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
