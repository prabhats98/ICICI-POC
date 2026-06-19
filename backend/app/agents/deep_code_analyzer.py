"""
Agent 5: Deep Code Analyzer - Performs Gemini-powered deep code-level
root cause analysis for incidents across all priority levels.

Provides:
  - Stack trace analysis & code-level bug identification
  - Exact fix suggestions with code snippets
  - Regression impact assessment
  - File/class/method pinpointing
"""

import logging
from typing import Any

from app.agents.state import PipelineState
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


DEEP_CODE_ANALYSIS_PROMPT = """You are a principal-level cloud infrastructure & software engineer at a major bank.
Perform a DEEP CODE-LEVEL root cause analysis for the following incident(s) detected in the banking cloud infrastructure.

INCIDENTS:
{incidents_text}

For EACH incident, provide a thorough, code-level analysis including:

## 1. Root Cause Identification
- Identify the exact root cause at the code/config level
- Pinpoint the likely file(s), class(es), method(s), or config key(s) involved
- Explain the failure chain: what triggered what

## 2. Stack Trace Analysis
- Reconstruct the likely call stack that produced this error
- Identify the frame where the failure originated
- Note any upstream callers that contributed

## 3. Code-Level Fix
- Provide the EXACT code changes needed (as diffs or code blocks)
- Include specific Azure CLI / PowerShell commands if infrastructure-related
- Show before/after config snippets if configuration-related

## 4. Regression Impact Assessment
- What other services/modules could be affected by this bug?
- What are the blast radius implications for the banking system?
- Are there related patterns in the codebase that might have the same bug?

## 5. Verification Steps
- How to verify the fix works (specific test commands, health checks)
- What monitoring alerts to set up to catch recurrence
- Recommended canary/rollout strategy

Return your analysis as valid JSON:
{{
  "analyses": [
    {{
      "incident_title": "<title>",
      "root_cause": {{
        "summary": "<one-line root cause>",
        "detail": "<detailed explanation>",
        "affected_files": ["<file paths>"],
        "affected_classes": ["<class names>"],
        "affected_methods": ["<method names>"],
        "failure_chain": "<A → B → C explanation>"
      }},
      "stack_trace": {{
        "reconstructed_trace": "<formatted stack trace>",
        "origin_frame": "<the frame where failure started>",
        "contributing_frames": ["<upstream contributors>"]
      }},
      "code_fix": {{
        "description": "<what the fix does>",
        "changes": [
          {{
            "file": "<file path>",
            "type": "code|config|infra",
            "before": "<original code/config>",
            "after": "<fixed code/config>",
            "explanation": "<why this change fixes it>"
          }}
        ],
        "commands": ["<CLI commands to execute if any>"]
      }},
      "regression_impact": {{
        "blast_radius": "low|medium|high|critical",
        "affected_services": ["<service names>"],
        "related_patterns": "<description of similar patterns>"
      }},
      "verification": {{
        "test_commands": ["<commands>"],
        "health_checks": ["<endpoints or checks>"],
        "monitoring_alerts": ["<alert descriptions>"]
      }}
    }}
  ]
}}
"""


async def deep_code_analyzer_node(
    state: PipelineState,
    priority: str,
) -> dict[str, Any]:
    """
    LangGraph Node: Perform deep code-level analysis for incidents of a given priority.

    Args:
        state: Current pipeline state
        priority: "high", "medium", or "low"

    Returns:
        Dict with deep_analysis_{priority} key containing the analysis results
    """
    priority_key = f"{priority}_priority_incidents"
    output_key = f"deep_analysis_{priority}"

    incidents = state.get(priority_key, [])
    logger.info(
        f"Agent 5 [Deep Code Analyzer - {priority.upper()}]: "
        f"Analyzing {len(incidents)} incidents..."
    )

    if not incidents:
        return {
            output_key: [],
            "current_agent": f"deep_code_analyzer_{priority}",
        }

    try:
        import json
        incidents_text = json.dumps(incidents, indent=2, default=str)
        prompt = DEEP_CODE_ANALYSIS_PROMPT.format(incidents_text=incidents_text)

        from google.genai.types import GenerateContentConfig
        from app.config import get_settings

        settings = get_settings()

        response = gemini_service.client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)
        analyses = result.get("analyses", [])

        logger.info(
            f"Agent 5 [Deep Code Analyzer - {priority.upper()}]: "
            f"Completed {len(analyses)} deep code analyses"
        )

        return {
            output_key: analyses,
            "current_agent": f"deep_code_analyzer_{priority}",
        }

    except Exception as e:
        logger.error(
            f"Agent 5 [Deep Code Analyzer - {priority.upper()}] failed: {e}"
        )
        return {
            output_key: [{"error": str(e)}],
            "current_agent": f"deep_code_analyzer_{priority}",
        }


# --- Priority-specific wrapper functions for LangGraph nodes ---

async def deep_code_analyzer_high_node(state: PipelineState) -> dict[str, Any]:
    """Deep code analysis for HIGH priority incidents."""
    return await deep_code_analyzer_node(state, "high")


async def deep_code_analyzer_medium_node(state: PipelineState) -> dict[str, Any]:
    """Deep code analysis for MEDIUM priority incidents."""
    return await deep_code_analyzer_node(state, "medium")


async def deep_code_analyzer_low_node(state: PipelineState) -> dict[str, Any]:
    """Deep code analysis for LOW priority incidents."""
    return await deep_code_analyzer_node(state, "low")
