"""
Gemini Service — Interface to Vertex AI Gemini for log analysis,
priority classification, context-aware resolution, and email generation.
"""

import json
import logging
import re
from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_json(text: str) -> dict:
    """Parse JSON from Gemini response, handling common formatting issues."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    cleaned = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError(f"Could not parse Gemini response", text, 0)


class GeminiService:
    """Service for interacting with Gemini via Vertex AI."""

    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_location,
        )
        self.model = settings.gemini_model

    async def classify_logs(self, logs: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Classification Agent: Analyze logs for incident type, intent, severity.
        """
        compact_logs = []
        for i, log in enumerate(logs):
            compact_logs.append({
                "idx": i,
                "ts": log.get("timestamp", ""),
                "level": log.get("level", ""),
                "source": log.get("source", ""),
                "category": log.get("category", ""),
                "msg": (log.get("message", "") or "")[:200],
                "resource": log.get("resource_id", ""),
                "op": log.get("operation_name", ""),
            })

        logs_text = json.dumps(compact_logs, indent=1, default=str)
        logger.info(f"Sending {len(compact_logs)} logs to Gemini ({len(logs_text)} chars)")

        prompt = f"""You are an expert Azure cloud infrastructure analyst for a banking system.
The logs come from Azure Front Door, Azure Application Gateway, Azure API Management, and Azure VM.

Analyze the following cloud logs and identify:
1. Errors and exceptions (5xx, timeouts, auth failures)
2. Traffic anomalies and spikes
3. Security-related events (WAF blocks, brute force, unauthorized)
4. Performance degradation (high latency, backend slowdowns)
5. Service health issues (unhealthy backends, probe failures)

For each issue found, provide:
- A clear title
- Severity score (1-10, where 10 is most critical)
- Affected Azure service
- Incident type (e.g., "Traffic Surge", "Auth Failure", "Backend Timeout")
- Brief description
- Potential root cause

Return as valid JSON:
{{
  "total_logs_analyzed": <int>,
  "issues_found": <int>,
  "summary": "<brief assessment>",
  "issues": [
    {{
      "title": "<title>",
      "severity": <1-10>,
      "affected_service": "<service>",
      "incident_type": "<type>",
      "description": "<description>",
      "root_cause": "<cause>",
      "related_log_indices": [<indices>]
    }}
  ]
}}

LOGS:
{logs_text}"""

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=16384,
                        response_mime_type="application/json",
                    ),
                )

                try:
                    response_text = response.text or ""
                except (ValueError, AttributeError):
                    response_text = ""

                if not response_text.strip():
                    if attempt < max_retries:
                        import asyncio
                        await asyncio.sleep(2)
                        continue
                    return {"total_logs_analyzed": len(logs), "issues_found": 0, "summary": "Empty response", "issues": []}

                result = _parse_json(response_text)
                logger.info(f"Classification complete: {result.get('issues_found', 0)} issues")
                return result

            except Exception as e:
                logger.error(f"Classification attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    import asyncio
                    await asyncio.sleep(2)
                    continue
                raise

    async def assign_priority(self, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Priority Agent: Classify each issue into P1 / P2 / P3.
        """
        issues_text = json.dumps(issues, indent=2, default=str)

        prompt = f"""You are a banking cloud operations priority classifier.
Classify each issue into priority levels:

- P1: Critical production outage, active security breach, data loss risk,
  service down, authentication failures at scale
- P2: Performance degradation, recurring non-critical errors, resource
  approaching limits, needs attention but not immediately service-impacting
- P3: Informational events, minor warnings, expected maintenance,
  non-impacting configuration changes

For each issue, provide:
- Priority: P1, P2, or P3
- A detailed category
- Banking-context enriched description
- Justification for the priority level

Return as valid JSON:
{{
  "classified_issues": [
    {{
      "original_title": "<from input>",
      "priority": "P1|P2|P3",
      "category": "<detailed category>",
      "incident_type": "<type>",
      "enriched_description": "<banking-context description>",
      "severity": <original severity>,
      "justification": "<why this priority>",
      "affected_service": "<service>"
    }}
  ]
}}

ISSUES:
{issues_text}"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                ),
            )
            result = _parse_json(response.text)
            return result.get("classified_issues", [])
        except Exception as e:
            logger.error(f"Priority assignment failed: {e}")
            raise

    async def generate_resolution(
        self, incident: dict[str, Any], historical_context: list[dict] | None = None
    ) -> str:
        """
        Resolution Agent: Generate a recommended fix or runbook.
        Includes historical context from past similar incidents.
        """
        context_section = ""
        if historical_context:
            context_section = "\n\nHISTORICAL CONTEXT (similar past incidents and their fixes):\n"
            for ctx in historical_context[:3]:
                context_section += f"- Past incident: {ctx.get('title', 'N/A')}\n"
                context_section += f"  Fix applied: {(ctx.get('solution', 'N/A') or 'N/A')[:300]}\n"

        prompt = f"""You are a senior Azure cloud solutions architect for a banking institution.
An incident has been detected in the banking cloud infrastructure.

INCIDENT DETAILS:
- Title: {incident.get('title', 'Unknown')}
- Priority: {incident.get('priority', 'Unknown')}
- Category: {incident.get('category', 'Unknown')}
- Description: {incident.get('description', 'No description')}
- Affected Service: {incident.get('affected_service', 'Unknown')}
- Root Cause: {incident.get('root_cause', 'Unknown')}
{context_section}

Provide a comprehensive resolution including:
1. **Immediate Action Steps** (what to do right now)
2. **Root Cause Resolution** (how to fix the underlying issue)
3. **Prevention Measures** (how to prevent recurrence)
4. **Monitoring Recommendations** (what to watch going forward)
5. **Rollback Plan** (if the fix causes issues)

Be specific with Azure CLI commands, configuration changes, and best practices.
Format in clear, actionable Markdown."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=4096,
                ),
            )
            return response.text
        except Exception as e:
            logger.error(f"Resolution generation failed: {e}")
            raise

    async def generate_email_body(
        self, incident: dict[str, Any], solution: str
    ) -> dict[str, str]:
        """Generate a professional email body for incident alerts."""
        prompt = f"""Generate a professional, urgent email for a banking production manager
about a cloud infrastructure incident.

INCIDENT:
- Title: {incident.get('title', 'Unknown')}
- Priority: {incident.get('priority', 'P1')}
- Category: {incident.get('category', 'Unknown')}
- Description: {incident.get('description', '')}

PROPOSED SOLUTION:
{solution}

Return as JSON with 'subject' and 'body' keys.
The body should be in HTML format.
Include severity indicators, clear action items, and the proposed solution."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=4096,
                    response_mime_type="application/json",
                ),
            )
            return _parse_json(response.text)
        except Exception as e:
            logger.error(f"Email generation failed: {e}")
            return {
                "subject": f"[{incident.get('priority', 'ALERT')}] Banking Cloud Alert: {incident.get('title', 'Unknown')}",
                "body": f"<h2>Incident Detected</h2><p>{incident.get('description', '')}</p><h3>Solution</h3><p>{solution}</p>",
            }


# Singleton
gemini_service = GeminiService()
