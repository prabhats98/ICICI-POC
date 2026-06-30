"""
Gemini Service — Interface to Vertex AI Gemini for log analysis,
priority classification, context-aware resolution, and email generation.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any

from google import genai
from google.genai.types import GenerateContentConfig

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_json(text: str) -> dict:
    """Parse JSON from Gemini response, handling thinking model output."""
    text = text.strip()

    # 1. Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Extract from ```json ... ``` blocks (handles thinking text before/after)
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Strip leading/trailing ``` if present
    stripped = text
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*\n?", "", stripped)
        stripped = re.sub(r"\n?```\s*$", "", stripped)
        try:
            return json.loads(stripped.strip())
        except json.JSONDecodeError:
            pass

    # 4. Remove trailing commas
    cleaned = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 5. Find first { ... } JSON object anywhere in text
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # 6. Greedy match for nested objects
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            # Try removing trailing commas in the match
            try:
                return json.loads(re.sub(r",\s*([}\]])", r"\1", match.group()))
            except json.JSONDecodeError:
                pass

    raise json.JSONDecodeError(f"Could not parse Gemini response", text, 0)


class GeminiService:
    """Service for interacting with Gemini via API key or Vertex AI."""

    def __init__(self):
        if settings.gemini_api_key:
            # Use API key mode (simpler, no JWT signing needed)
            self.client = genai.Client(api_key=settings.gemini_api_key)
            logger.info("Gemini initialized with API key")
        else:
            # Use Vertex AI mode (requires service account)
            self.client = genai.Client(
                vertexai=True,
                project=settings.gcp_project_id,
                location=settings.gcp_location,
            )
            logger.info("Gemini initialized with Vertex AI")
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

CRITICAL RULES:
- ONLY report issues that have CLEAR EVIDENCE in the logs (HTTP 5xx/4xx status codes, error messages, exceptions, timeouts, WAF blocks).
- DO NOT create issues from HTTP 200/2xx success logs. Traffic spikes with 200 status codes are NORMAL and NOT incidents.
- DO NOT speculate about "hidden" or "masked" errors if the logs show successful responses.
- If ALL logs show successful (2xx) responses with no errors, return 0 issues.
- Each issue MUST reference specific log indices that prove the error exists.

Analyze the following cloud logs and identify ONLY:
1. Actual errors and exceptions (5xx HTTP codes, timeouts, auth failures)
2. WAF blocks and security events (blocked requests, brute force)
3. Backend health probe failures (unhealthy status)
4. Actual performance issues with error evidence (502/504 timeouts)

For each REAL issue found, provide:
- A clear title
- Severity score (1-10, where 10=most critical). Use 8-10 ONLY for 5xx errors affecting critical endpoints.
- Affected Azure service (include the specific resource name from resource_id if available)
- Incident type (e.g., "Backend 502 Error", "WAF Block", "Health Probe Failure")
- Brief description citing ACTUAL error codes/messages from the logs
- Root cause based on actual log evidence
- The specific URL or endpoint path where the error is occurring (extract from log message or requestUri)

Return as valid JSON:
{{
  "total_logs_analyzed": <int>,
  "issues_found": <int>,
  "summary": "<brief assessment>",
  "issues": [
    {{
      "title": "<title>",
      "severity": <1-10>,
      "affected_service": "<service with resource name>",
      "incident_type": "<type>",
      "description": "<description with actual error codes>",
      "root_cause": "<cause based on log evidence>",
      "sample_endpoint": "<the URL/endpoint where error occurs, e.g. /mail/send or https://app.azurewebsites.net/api/v1/...>",
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
                    ),
                )

                try:
                    response_text = response.text or ""
                except (ValueError, AttributeError):
                    response_text = ""

                # For thinking models, text might be across multiple parts
                if not response_text.strip() and response.candidates:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'text') and part.text and not getattr(part, 'thought', False):
                            response_text = part.text
                            break

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

        max_retries = 2
        for attempt in range(max_retries + 1):
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

                try:
                    response_text = response.text or ""
                except (ValueError, AttributeError):
                    response_text = ""

                if not response_text.strip():
                    if attempt < max_retries:
                        import asyncio
                        await asyncio.sleep(2)
                        continue
                    # Fallback: return issues with default P2 priority
                    logger.warning("Priority assignment: empty Gemini response, using defaults")
                    return [
                        {
                            "original_title": issue.get("title", "Unknown"),
                            "priority": "P2",
                            "category": issue.get("incident_type", "Uncategorized"),
                            "incident_type": issue.get("incident_type", ""),
                            "enriched_description": issue.get("description", ""),
                            "severity": issue.get("severity", 5),
                            "justification": "Default P2 — Gemini response was empty",
                            "affected_service": issue.get("affected_service", "Unknown"),
                        }
                        for issue in issues
                    ]

                result = _parse_json(response_text)
                return result.get("classified_issues", [])

            except Exception as e:
                logger.error(f"Priority assignment attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    import asyncio
                    await asyncio.sleep(2)
                    continue
                # Final fallback: return issues with default P2 priority
                logger.warning("Priority assignment: all retries failed, using defaults")
                return [
                    {
                        "original_title": issue.get("title", "Unknown"),
                        "priority": "P2",
                        "category": issue.get("incident_type", "Uncategorized"),
                        "incident_type": issue.get("incident_type", ""),
                        "enriched_description": issue.get("description", ""),
                        "severity": issue.get("severity", 5),
                        "justification": f"Default P2 — priority classification failed: {str(e)}",
                        "affected_service": issue.get("affected_service", "Unknown"),
                    }
                    for issue in issues
                ]

    async def generate_root_cause(self, issue: dict[str, Any]) -> dict[str, Any]:
        """
        RCA Agent: Use Gemini to generate a detailed, log-specific root cause analysis.
        Sends actual error samples and incident details to get a contextual RCA
        instead of generic hardcoded patterns.
        """
        title = issue.get("title", "Unknown Issue")
        description = issue.get("description", "")
        category = issue.get("category", "")
        source_service = issue.get("source_service", "Unknown")
        sample_logs = issue.get("sample_logs", [])
        log_count = issue.get("log_count", 0)

        # Build a rich context for Gemini
        log_samples_text = ""
        if sample_logs:
            log_samples_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(sample_logs[:10]))
        else:
            log_samples_text = "  (No actual error logs with error codes/messages were found in this time range. Base your analysis ONLY on the incident description. Set confidence_score to 0.3 or lower.)"

        sample_endpoint = issue.get("sample_endpoint", "")

        prompt = f"""You are an expert Azure Cloud Infrastructure RCA analyst for ICICI Prudential (banking/insurance).
Analyze this incident and provide a SPECIFIC, DETAILED root cause analysis based on the actual error logs below.

## Incident Details
- **Title**: {title}
- **Category**: {category}
- **Affected Service**: {source_service}
- **Error Count**: {log_count} occurrences
- **Description**: {description[:500]}
{f'- **Affected Endpoint**: {sample_endpoint}' if sample_endpoint else ''}

## Actual Error Log Samples
{log_samples_text}

## Instructions
Based on the ACTUAL error log content above (not generic patterns), determine:
1. The specific root cause — what exactly went wrong, referencing actual error messages/codes from the logs
2. The RCA category (e.g., "SQL Lock Timeout", "App Service Crash", "WAF Geo-Block", "DNS Failure", "Backend 502", "SSL Certificate Warning", "Insecure HTTPS Connection", etc.)
3. Which specific Azure component is affected (e.g., "Azure SQL Database - ipru-inc-prod-solus-da-sql-server", "Azure App Service - ICICI portal", etc.)
4. What immediate action should be taken
5. What preventive measures to implement
6. Business impact assessment
7. Which team should own resolution

CRITICAL RULES:
- NEVER say "the log only shows a write operation" or "insufficient information to determine root cause" — that is UNACCEPTABLE.
- ALWAYS derive a SPECIFIC root cause from the incident title, category, description, affected service, error count, and log samples.
- If log samples show WAF/Firewall activity, explain WHAT the WAF detected (e.g., geo-blocking, SQL injection attempt, bot scanning, rate limiting).
- If log samples show SSL/TLS warnings, explain the security risk (e.g., unverified HTTPS to third-party API, missing certificate validation).
- If log samples show Python/application stack traces, identify the library, function, and error type.
- Reference SPECIFIC error messages, error codes, URLs, hostnames, IP addresses from the logs.
- If you see HTTP status codes, explain what they mean in the context of this Azure service.
- The root_cause field MUST be 2-4 detailed sentences citing real evidence from the logs.
- Do NOT use generic descriptions like "Backend unavailable" — be SPECIFIC about what the logs show.

Return a JSON object with these fields:
{{
  "root_cause": "Specific root cause based on the actual error logs (2-4 sentences, referencing real errors)",
  "root_cause_category": "Precise category (e.g. SQL Lock Timeout, App Service HTTP 500, WAF Country Block, SSL Certificate Warning)",
  "affected_component": "Specific Azure resource (include resource name if visible in logs)",
  "confidence_score": 0.85,
  "immediate_resolution": "Step-by-step resolution (numbered list)",
  "preventive_action": "Preventive measures (numbered list)",
  "business_impact": "Impact assessment",
  "owner_team": "Team name",
  "est_resolution_min": 30
}}"""

        try:
            import asyncio, time as _time
            loop = asyncio.get_event_loop()

            # Retry up to 2 times for rate limit / 503 errors
            last_err = None
            for attempt in range(3):
                try:
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.client.models.generate_content(
                            model=self.model,
                            contents=prompt,
                            config=GenerateContentConfig(
                                temperature=0.2,
                                max_output_tokens=8192,
                            ),
                        ),
                    )
                    break  # Success
                except Exception as retry_err:
                    last_err = retry_err
                    err_str = str(retry_err)
                    if "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str:
                        wait = 5 * (attempt + 1)
                        logger.warning(f"Gemini RCA rate limited (attempt {attempt+1}/3), waiting {wait}s...")
                        await asyncio.sleep(wait)
                    else:
                        raise
            else:
                raise last_err

            # Extract text from response — handle thinking models
            response_text = ""
            try:
                response_text = response.text or ""
            except Exception:
                pass

            # For thinking models, text might be across multiple parts
            if not response_text.strip() and response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text and not getattr(part, 'thought', False):
                        response_text = part.text
                        break

            if not response_text.strip():
                logger.warning(f"Gemini RCA returned empty response for: {title[:50]}")
                return {}

            logger.info(f"Gemini RCA raw response ({len(response_text)} chars): {response_text[:100]}...")

            result = _parse_json(response_text)
            if result and "root_cause" in result:
                logger.info(f"Gemini AI RCA: {result.get('root_cause_category', '?')} → {result['root_cause'][:80]}")
                return result
            else:
                logger.warning(f"Gemini RCA returned unexpected format: {response_text[:200]}")
                return {}

        except Exception as e:
            logger.error(f"Gemini RCA generation failed: {e}")
            return {}

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
        """Generate a professional, data-driven email body for incident alerts.
        
        Uses REAL pipeline data — root cause, affected component, service name,
        confidence score, resolution steps, and business impact.
        """
        priority = incident.get('priority', 'P1')
        title = incident.get('title', 'Unknown Incident')
        category = incident.get('category', 'Unknown')
        description = incident.get('description', 'No description available.')
        source_service = incident.get('source_service', incident.get('affected_service', 'Unknown'))
        
        # RCA data from pipeline
        root_cause = incident.get('root_cause', 'Under investigation')
        root_cause_category = incident.get('root_cause_category', '')
        confidence_score = incident.get('confidence_score', 0)
        affected_component = incident.get('affected_component', 'Under analysis')
        owner_team = incident.get('owner_team', 'Platform Engineering')
        business_impact = incident.get('business_impact', '')
        immediate_resolution = incident.get('immediate_resolution', '')
        preventive_action = incident.get('preventive_action', '')
        incident_type = incident.get('incident_type', '')
        sample_endpoint = incident.get('sample_endpoint', '')

        # Incident date/time (when it happened)
        incident_start = incident.get('start_date', '')
        incident_end = incident.get('end_date', '')
        incident_time_range = incident.get('incident_time_range', '')

        # Format the date/time for display
        incident_datetime_display = ''
        if incident_start and incident_end:
            try:
                from datetime import datetime as dt_parse
                s = dt_parse.fromisoformat(incident_start.replace('Z', '+00:00'))
                e = dt_parse.fromisoformat(incident_end.replace('Z', '+00:00'))
                incident_datetime_display = f"{s.strftime('%d %B %Y, %I:%M %p')} — {e.strftime('%I:%M %p IST')}"
            except Exception:
                incident_datetime_display = incident_time_range or f"{incident_start} to {incident_end}"
        elif incident_time_range:
            incident_datetime_display = incident_time_range

        # Priority styling
        priority_color = {'P1': '#dc2626', 'P2': '#d97706', 'P3': '#059669'}.get(priority, '#6b7280')
        priority_label = {'P1': 'Critical', 'P2': 'High', 'P3': 'Informational'}.get(priority, 'Unknown')

        # Build resolution HTML — keep up to 8 steps
        resolution_items = []
        if immediate_resolution:
            for line in immediate_resolution.split('\n'):
                line = line.strip().lstrip('-*• ').strip()
                if line and len(line) > 10:
                    resolution_items.append(line[:250])
        if not resolution_items:
            solution_clean = (solution or '').replace('**', '').replace('```', '').strip()
            for para in solution_clean.split('\n'):
                para = para.strip().lstrip('-*• 0123456789.').strip()
                if para and len(para) > 10:
                    resolution_items.append(para[:250])

        resolution_html = ''
        if resolution_items:
            resolution_html = '<ol style="margin: 0; padding-left: 20px;">'
            for item in resolution_items[:8]:
                resolution_html += f'<li style="margin-bottom: 6px; color: #cbd5e1; line-height: 1.5; font-size: 13px;">{item}</li>\n'
            resolution_html += '</ol>'
        else:
            resolution_html = '<p style="margin: 0; color: #cbd5e1; font-size: 13px;">Investigation in progress.</p>'

        # Build preventive actions — up to 5
        preventive_html = ''
        if preventive_action:
            prev_items = [l.strip().lstrip('-*• ').strip()[:200] for l in preventive_action.split('\n') if l.strip() and len(l.strip()) > 10]
            if prev_items:
                preventive_html = f'''
                <div style="background: rgba(99,102,241,0.06); border-radius: 10px; padding: 16px; margin-bottom: 16px; border-left: 3px solid #6366f1;">
                  <h3 style="margin: 0 0 10px; color: #818cf8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 700;">🔒 Preventive Actions</h3>
                  <ol style="margin: 0; padding-left: 20px;">
                    {''.join(f'<li style="margin-bottom: 4px; color: #cbd5e1; font-size: 13px; line-height: 1.5;">{p}</li>' for p in prev_items[:5])}
                  </ol>
                </div>'''

        # Confidence badge
        conf_pct = round(confidence_score * 100) if confidence_score else 0
        conf_color = '#10b981' if conf_pct >= 80 else '#d97706' if conf_pct >= 50 else '#dc2626'

        # Header labels per priority
        if priority == 'P1':
            header_label = '🔴 CRITICAL — Production Incident Alert'
            status_label = 'Emergency Response Activated'
        elif priority == 'P2':
            header_label = '🟡 WARNING — Infrastructure Alert'
            status_label = f'RCA Identified — {(root_cause_category or root_cause)[:60]}'
        else:
            header_label = '🟢 INFO — Monitoring Alert'
            status_label = 'Under Review'

        # Azure Portal URL for the resource
        resource_id = ''
        sample_logs_section = ''

        # Extract error log samples from description
        sample_logs = incident.get('sample_logs', [])
        if not sample_logs and description:
            lines = description.split('\n')
            for line in lines:
                line = line.strip().lstrip('•- ')
                if line and ('HTTP' in line or 'error' in line.lower() or 'SQL' in line or 'timeout' in line.lower() or 'exception' in line.lower()):
                    sample_logs.append(line[:200])
                if len(sample_logs) >= 5:
                    break

        if sample_logs:
            log_rows = ''
            for i, log_text in enumerate(sample_logs[:5]):
                bg = '#1a1f2e' if i % 2 == 0 else '#141825'
                log_rows += f'<tr><td style="padding: 8px 12px; color: #ef4444; font-size: 11px; font-weight: 600; white-space: nowrap; vertical-align: top;">ERROR</td><td style="padding: 8px 12px; color: #e2e8f0; font-size: 12px; font-family: Consolas, monospace; line-height: 1.4; background: {bg}; word-break: break-all;">{log_text}</td></tr>'

            sample_logs_section = f'''
            <div style="background: rgba(239,68,68,0.06); border-radius: 10px; padding: 16px; margin-bottom: 16px; border-left: 3px solid #ef4444;">
              <h3 style="margin: 0 0 10px; color: #ef4444; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 700;">📋 Actual Error Logs</h3>
              <table style="width: 100%; border-collapse: collapse; border-radius: 8px; overflow: hidden;">
                <tr style="background: #0f172a;">
                  <th style="text-align: left; padding: 6px 12px; color: #64748b; font-size: 10px; font-weight: 700; text-transform: uppercase; width: 60px;">Level</th>
                  <th style="text-align: left; padding: 6px 12px; color: #64748b; font-size: 10px; font-weight: 700; text-transform: uppercase;">Error Details</th>
                </tr>
                {log_rows}
              </table>
            </div>'''

        # Azure Portal URL
        azure_portal_url = ''
        raw_resource_id = incident.get('resource_id', '')
        if not raw_resource_id:
            desc_lower = (description or '').lower()
            if 'ipruincprod' in desc_lower:
                raw_resource_id = 'IPRUINCPROD'

        if raw_resource_id and '/subscriptions/' in raw_resource_id:
            azure_portal_url = f'https://portal.azure.com/#@/resource{raw_resource_id}'
        elif source_service and 'Azure' in source_service:
            azure_portal_url = 'https://portal.azure.com'

        azure_link_html = ''
        if azure_portal_url:
            azure_link_html = f'''
            <tr>
              <td style="padding: 8px 0; color: #64748b; font-size: 13px; font-weight: 600; vertical-align: top;">Azure Portal:</td>
              <td style="padding: 8px 0;"><a href="{azure_portal_url}" style="color: #60a5fa; font-size: 13px; text-decoration: none;">Open in Azure Portal →</a></td>
            </tr>'''

        # Affected Endpoint URL
        endpoint_html = ''
        if sample_endpoint:
            endpoint_html = f'''
            <tr>
              <td style="padding: 8px 0; color: #64748b; font-size: 13px; font-weight: 600; vertical-align: top;">Affected URL:</td>
              <td style="padding: 8px 0; color: #ef4444; font-size: 13px; font-weight: 600; font-family: Consolas, monospace; word-break: break-all;">{sample_endpoint}</td>
            </tr>'''

        # Affected Website Pages section — extract all URLs from logs
        affected_urls = incident.get('affected_urls', [])
        if not affected_urls and sample_endpoint:
            affected_urls = [sample_endpoint]

        affected_pages_html = ''
        if affected_urls:
            url_rows = ''
            for i, url in enumerate(affected_urls[:5]):
                icon = '🔴' if 'icicipruamc' in url or 'ipruinc' in url else '🟡'
                url_rows += f'''<tr>
                  <td style="padding: 6px 8px; color: #94a3b8; font-size: 12px; text-align: center; width: 30px;">{icon}</td>
                  <td style="padding: 6px 8px; color: #60a5fa; font-size: 12px; font-family: Consolas, monospace; word-break: break-all;">
                    <a href="{url}" style="color: #60a5fa; text-decoration: none;">{url}</a>
                  </td>
                </tr>'''
            affected_pages_html = f'''
            <div style="background: rgba(59,130,246,0.06); border-radius: 10px; padding: 16px; margin-bottom: 16px; border-left: 3px solid #3b82f6;">
              <h3 style="margin: 0 0 10px; color: #3b82f6; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 700;">🌐 Affected Website Pages</h3>
              <p style="margin: 0 0 8px; color: #94a3b8; font-size: 11px;">The following pages on icicipruamc.com / Azure App Service are experiencing errors:</p>
              <table style="width: 100%; border-collapse: collapse;">
                {url_rows}
              </table>
            </div>'''

        # Truncate long fields
        root_cause_display = (root_cause or 'Under investigation')[:400]
        description_display = (description or '')[:500]
        business_impact_display = (business_impact or '')[:400]

        # Next Steps section
        next_steps_html = f'''
        <div style="background: rgba(251,191,36,0.06); border-radius: 10px; padding: 16px; margin-bottom: 16px; border-left: 3px solid #fbbf24;">
          <h3 style="margin: 0 0 10px; color: #fbbf24; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 700;">📌 Immediate Next Steps</h3>
          <table style="width: 100%; border-collapse: collapse;">
            <tr>
              <td style="padding: 5px 8px; color: #f59e0b; font-size: 14px; width: 24px; vertical-align: top;">1.</td>
              <td style="padding: 5px 8px; color: #e2e8f0; font-size: 13px; line-height: 1.5;"><strong>Acknowledge Incident</strong> — Assign an owner from {owner_team} and update the incident ticket status</td>
            </tr>
            <tr>
              <td style="padding: 5px 8px; color: #f59e0b; font-size: 14px; width: 24px; vertical-align: top;">2.</td>
              <td style="padding: 5px 8px; color: #e2e8f0; font-size: 13px; line-height: 1.5;"><strong>Verify Impact</strong> — Check if {sample_endpoint or 'the affected endpoint'} is currently returning errors in Azure Monitor / Application Insights</td>
            </tr>
            <tr>
              <td style="padding: 5px 8px; color: #f59e0b; font-size: 14px; width: 24px; vertical-align: top;">3.</td>
              <td style="padding: 5px 8px; color: #e2e8f0; font-size: 13px; line-height: 1.5;"><strong>Apply Resolution</strong> — Follow the resolution steps below and validate the fix on {source_service}</td>
            </tr>
            <tr>
              <td style="padding: 5px 8px; color: #f59e0b; font-size: 14px; width: 24px; vertical-align: top;">4.</td>
              <td style="padding: 5px 8px; color: #e2e8f0; font-size: 13px; line-height: 1.5;"><strong>Monitor</strong> — Watch for recurrence in the next 30 minutes via Azure Portal and CloudGuard dashboard</td>
            </tr>
            <tr>
              <td style="padding: 5px 8px; color: #f59e0b; font-size: 14px; width: 24px; vertical-align: top;">5.</td>
              <td style="padding: 5px 8px; color: #e2e8f0; font-size: 13px; line-height: 1.5;"><strong>Post-Incident Review</strong> — Document the RCA and update the runbook for {root_cause_category or category}</td>
            </tr>
          </table>
        </div>'''

        # Escalation matrix
        escalation_sla = {'P1': '15 minutes', 'P2': '1 hour', 'P3': '4 hours'}.get(priority, '4 hours')
        escalation_html = f'''
        <div style="background: rgba(255,255,255,0.03); border-radius: 10px; padding: 16px; margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.06);">
          <h3 style="margin: 0 0 10px; color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 700;">📞 Escalation & SLA</h3>
          <table style="width: 100%; border-collapse: collapse;">
            <tr>
              <td style="padding: 4px 0; color: #64748b; font-size: 12px; font-weight: 600; width: 140px;">Owner Team:</td>
              <td style="padding: 4px 0; color: #e2e8f0; font-size: 13px; font-weight: 600;">{owner_team}</td>
            </tr>
            <tr>
              <td style="padding: 4px 0; color: #64748b; font-size: 12px; font-weight: 600;">Response SLA:</td>
              <td style="padding: 4px 0; color: #fbbf24; font-size: 13px; font-weight: 700;">{escalation_sla}</td>
            </tr>
            <tr>
              <td style="padding: 4px 0; color: #64748b; font-size: 12px; font-weight: 600;">Escalation:</td>
              <td style="padding: 4px 0; color: #e2e8f0; font-size: 13px;">If unresolved within {escalation_sla}, escalate to L2 / Infrastructure Lead</td>
            </tr>
          </table>
        </div>'''

        subject = f"[{priority}] {source_service}: {title}"
        if incident_datetime_display:
            subject = f"[{priority}] {source_service}: {title} ({incident_datetime_display})"

        # Build concise, data-driven email
        incident_ref = incident.get('incident_id', incident.get('id', 'CG-' + datetime.now().strftime('%Y%m%d%H%M')))
        fallback_body = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 680px; margin: 0 auto; background: #0f172a; color: #e2e8f0; border-radius: 12px; overflow: hidden; border: 1px solid #1e293b;">
          <!-- Header -->
          <div style="background: {priority_color}; padding: 18px 24px;">
            <h1 style="margin: 0; font-size: 18px; color: #fff; font-weight: 700;">{header_label}</h1>
          </div>

          <div style="padding: 24px;">
            <!-- Incident Title -->
            <h2 style="color: #f1f5f9; font-size: 17px; margin: 0 0 10px; font-weight: 700;">{title}</h2>
            <div style="display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap;">
              <span style="background: rgba(255,255,255,0.08); border-radius: 6px; padding: 4px 12px; font-size: 12px; color: #94a3b8;">☁️ {source_service}</span>
              <span style="background: {priority_color}22; border: 1px solid {priority_color}; border-radius: 6px; padding: 4px 12px; font-size: 12px; color: {priority_color}; font-weight: 700;">{priority} — {priority_label}</span>
            </div>

            <!-- Incident Details -->
            <div style="background: rgba(255,255,255,0.04); border-radius: 10px; padding: 16px; margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.06);">
              <table style="width: 100%; border-collapse: collapse;">
                <tr>
                  <td style="padding: 6px 0; color: #64748b; font-size: 12px; font-weight: 600; width: 150px;">Incident Ref:</td>
                  <td style="padding: 6px 0; color: #e2e8f0; font-size: 13px; font-weight: 600; font-family: Consolas, monospace;">{incident_ref}</td>
                </tr>
                <tr>
                  <td style="padding: 6px 0; color: #64748b; font-size: 12px; font-weight: 600;">Affected Service:</td>
                  <td style="padding: 6px 0; color: #e2e8f0; font-size: 13px; font-weight: 600;">{source_service}</td>
                </tr>
                <tr>
                  <td style="padding: 6px 0; color: #64748b; font-size: 12px; font-weight: 600;">Affected Component:</td>
                  <td style="padding: 6px 0; color: #e2e8f0; font-size: 13px;">{affected_component}</td>
                </tr>
                <tr>
                  <td style="padding: 6px 0; color: #64748b; font-size: 12px; font-weight: 600;">Category:</td>
                  <td style="padding: 6px 0; color: #e2e8f0; font-size: 13px;">{category}</td>
                </tr>
                <tr>
                  <td style="padding: 6px 0; color: #64748b; font-size: 12px; font-weight: 600;">Status:</td>
                  <td style="padding: 6px 0; color: #fbbf24; font-size: 13px; font-weight: 600;">{status_label}</td>
                </tr>
                {'<tr><td style="padding: 6px 0; color: #64748b; font-size: 12px; font-weight: 600;">Incident Time:</td><td style="padding: 6px 0; color: #f59e0b; font-size: 13px; font-weight: 700;">' + incident_datetime_display + '</td></tr>' if incident_datetime_display else ''}
                {azure_link_html}
                {endpoint_html}
              </table>
            </div>

            <!-- Affected Website Pages -->
            {affected_pages_html}

            <!-- Root Cause Analysis -->
            <div style="background: rgba(255,255,255,0.04); border-radius: 10px; padding: 16px; margin-bottom: 16px; border-left: 3px solid {priority_color};">
              <h3 style="margin: 0 0 8px; color: {priority_color}; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 700;">🔍 Root Cause Analysis</h3>
              <p style="margin: 0 0 8px; color: #f1f5f9; font-size: 13px; font-weight: 600; line-height: 1.5;">{root_cause_display}</p>
              <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                <span style="color: #64748b; font-size: 11px;">Category: <strong style="color: #e2e8f0;">{root_cause_category or category}</strong></span>
                <span style="color: #64748b; font-size: 11px;">Confidence: <strong style="color: {conf_color};">{conf_pct}%</strong></span>
                <span style="color: #64748b; font-size: 11px;">Team: <strong style="color: #e2e8f0;">{owner_team}</strong></span>
              </div>
            </div>

            {sample_logs_section}

            {'<div style="background: rgba(255,255,255,0.04); border-radius: 10px; padding: 16px; margin-bottom: 16px; border-left: 3px solid #64748b;"><h3 style="margin: 0 0 8px; color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 700;">⚠ Business Impact</h3><p style="margin: 0; color: #cbd5e1; line-height: 1.5; font-size: 13px;">' + business_impact_display + '</p></div>' if business_impact_display else ''}

            <!-- Immediate Next Steps -->
            {next_steps_html}

            <!-- Resolution Steps -->
            <div style="background: rgba(16,185,129,0.06); border-radius: 10px; padding: 16px; margin-bottom: 16px; border-left: 3px solid #10b981;">
              <h3 style="margin: 0 0 10px; color: #10b981; font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 700;">🛠 Detailed Resolution Steps</h3>
              {resolution_html}
            </div>

            {preventive_html}

            <!-- Escalation & SLA -->
            {escalation_html}

            <!-- Sign-off -->
            <div style="margin-top: 16px; padding-top: 14px; border-top: 1px solid rgba(255,255,255,0.06);">
              <p style="margin: 0 0 2px; color: #f1f5f9; font-size: 13px; font-weight: 700;">CloudGuard Incident Response System</p>
              <p style="margin: 0; color: #64748b; font-size: 11px;">AI-Powered Azure Cloud Log Intelligence • ICICI Prudential AMC • KR Elixir Technology</p>
            </div>
          </div>

          <!-- Footer -->
          <div style="padding: 12px 24px; background: rgba(0,0,0,0.3); text-align: center; border-top: 1px solid rgba(255,255,255,0.04);">
            <p style="margin: 0; color: #475569; font-size: 10px;">Incident Ref: {incident_ref} • Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} • Target: icicipruamc.com</p>
          </div>
        </div>
        """

        return {"subject": subject, "body": fallback_body}




# Singleton
gemini_service = GeminiService()
