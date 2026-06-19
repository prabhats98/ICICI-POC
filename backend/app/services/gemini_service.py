"""
Gemini Service - Interface to Vertex AI Gemini 2.5 Flash for log analysis,
priority classification, and solution generation.
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
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Remove trailing commas before } or ]
    cleaned = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Try to find the first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    raise json.JSONDecodeError(f"Could not parse Gemini response", text, 0)


class GeminiService:
    """Service for interacting with Gemini 2.5 Flash via Vertex AI."""

    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_location,
        )
        self.model = settings.gemini_model

    async def analyze_logs(self, logs: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Agent 2: Analyze cloud logs for anomalies, spikes, and errors.
        Returns structured analysis with severity scores.
        """
        # Compact logs to reduce token usage — truncate messages, drop verbose fields
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
Analyze the following cloud logs and identify:
1. Errors and exceptions
2. Anomalous patterns or spikes
3. Security-related events
4. Performance degradation indicators
5. Service health issues

For each issue found, provide:
- A clear title
- Severity score (1-10, where 10 is most critical)
- Affected Azure service/resource
- Brief description of the issue
- Potential root cause

Return your analysis as a valid JSON object with this structure:
{{
  "total_logs_analyzed": <int>,
  "issues_found": <int>,
  "summary": "<brief overall assessment>",
  "issues": [
    {{
      "title": "<issue title>",
      "severity": <1-10>,
      "affected_service": "<service name>",
      "description": "<description>",
      "root_cause": "<potential root cause>",
      "related_log_indices": [<indices of related logs>]
    }}
  ]
}}

LOGS TO ANALYZE:
{logs_text}"""

        max_retries = 2
        last_error = None

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

                # Safely access response.text — it can raise ValueError if blocked
                try:
                    response_text = response.text or ""
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Gemini response.text raised {type(e).__name__}: {e}")
                    response_text = ""

                if not response_text.strip():
                    logger.warning(
                        f"Gemini returned empty response (attempt {attempt + 1}/{max_retries + 1}). "
                        f"Candidates: {getattr(response, 'candidates', 'N/A')}"
                    )
                    if attempt < max_retries:
                        import asyncio
                        await asyncio.sleep(2)
                        continue
                    return {
                        "total_logs_analyzed": len(logs),
                        "issues_found": 0,
                        "summary": "Gemini returned empty responses after retries — possible safety filter or token limit.",
                        "issues": [],
                    }

                result = _parse_json(response_text)
                logger.info(f"Gemini analysis complete: {result.get('issues_found', 0)} issues found")
                return result

            except Exception as e:
                last_error = e
                logger.error(f"Gemini analysis attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    import asyncio
                    await asyncio.sleep(2)
                    continue
                raise

    async def classify_priority(self, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Agent 3: Classify each issue into HIGH, MEDIUM, or LOW priority.
        """
        issues_text = json.dumps(issues, indent=2, default=str)

        prompt = f"""You are a banking cloud operations priority classifier.
Classify each of the following detected issues into priority levels:

- HIGH: Critical production issues affecting banking services, security breaches,
  data loss risks, service outages, authentication failures at scale
- MEDIUM: Performance degradation, non-critical errors recurring, resource usage anomalies,
  issues that need attention but are not immediately service-impacting
- LOW: Informational events, minor warnings, expected maintenance events,
  non-impacting configuration changes

For each issue, also provide:
- A detailed category (e.g., "Authentication Failure", "Resource Exhaustion", "Network Timeout")
- An enriched description with banking context

Return as valid JSON:
{{
  "classified_issues": [
    {{
      "original_title": "<from input>",
      "priority": "HIGH|MEDIUM|LOW",
      "category": "<detailed category>",
      "enriched_description": "<banking-context description>",
      "severity": <original severity>,
      "justification": "<why this priority>"
    }}
  ]
}}

ISSUES TO CLASSIFY:
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
            logger.info(f"Priority classification complete")
            return result.get("classified_issues", [])
        except Exception as e:
            logger.error(f"Priority classification failed: {e}")
            raise

    async def generate_solution(self, incident: dict[str, Any]) -> str:
        """
        Agent 4a/4b: Generate a detailed solution for an incident.
        """
        prompt = f"""You are a senior Azure cloud solutions architect for a banking institution.
A critical incident has been detected in the banking cloud infrastructure.

INCIDENT DETAILS:
- Title: {incident.get('title', 'Unknown')}
- Priority: {incident.get('priority', 'Unknown')}
- Category: {incident.get('category', 'Unknown')}
- Description: {incident.get('description', 'No description')}
- Affected Service: {incident.get('affected_service', 'Unknown')}
- Root Cause: {incident.get('root_cause', 'Unknown')}

Provide a comprehensive solution including:
1. **Immediate Action Steps** (what to do right now)
2. **Root Cause Resolution** (how to fix the underlying issue)
3. **Prevention Measures** (how to prevent recurrence)
4. **Monitoring Recommendations** (what to watch going forward)
5. **Rollback Plan** (if the fix causes issues)

Be specific with Azure CLI commands, configuration changes, and best practices.
Format the response in clear, actionable Markdown."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=4096,
                ),
            )
            logger.info(f"Solution generated for incident: {incident.get('title', 'Unknown')}")
            return response.text
        except Exception as e:
            logger.error(f"Solution generation failed: {e}")
            raise

    async def generate_email_body(
        self, incident: dict[str, Any], solution: str
    ) -> dict[str, str]:
        """
        Generate a professional email body for high-priority alerts.
        Returns dict with 'subject' and 'body' keys.
        """
        prompt = f"""Generate a professional, urgent email for a banking production manager
about a critical cloud infrastructure incident.

INCIDENT:
- Title: {incident.get('title', 'Unknown')}
- Priority: {incident.get('priority', 'HIGH')}
- Category: {incident.get('category', 'Unknown')}
- Description: {incident.get('description', '')}

PROPOSED SOLUTION:
{solution}

Return as JSON with 'subject' and 'body' keys.
The body should be in HTML format suitable for an email client.
Include severity indicators, clear action items, and the proposed solution.
Keep it professional and urgent but not panicked."""

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
            result = _parse_json(response.text)
            return result
        except Exception as e:
            logger.error(f"Email generation failed: {e}")
            return {
                "subject": f"[CRITICAL] Banking Cloud Alert: {incident.get('title', 'Unknown Incident')}",
                "body": f"<h2>Critical Incident Detected</h2><p>{incident.get('description', '')}</p><h3>Solution</h3><p>{solution}</p>",
            }


# Singleton instance
gemini_service = GeminiService()
