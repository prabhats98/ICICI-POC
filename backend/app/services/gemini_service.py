"""
Gemini Service - Interface to Vertex AI Gemini 2.5 Flash for log analysis,
priority classification, and solution generation.
"""

import json
import logging
from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


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
        logs_text = json.dumps(logs, indent=2, default=str)

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

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                ),
            )
            result = json.loads(response.text)
            logger.info(f"Gemini analysis complete: {result.get('issues_found', 0)} issues found")
            return result
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
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
            result = json.loads(response.text)
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
            result = json.loads(response.text)
            return result
        except Exception as e:
            logger.error(f"Email generation failed: {e}")
            return {
                "subject": f"[CRITICAL] Banking Cloud Alert: {incident.get('title', 'Unknown Incident')}",
                "body": f"<h2>Critical Incident Detected</h2><p>{incident.get('description', '')}</p><h3>Solution</h3><p>{solution}</p>",
            }


# Singleton instance
gemini_service = GeminiService()
