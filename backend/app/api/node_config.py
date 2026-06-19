"""
Node Configuration API - View/edit per-node configuration for the agent pipeline.
In-memory config store with defaults; resets on server restart.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/workflow/nodes", tags=["Node Config"])


# --- Default config per node ---

def _default_configs() -> dict[str, dict[str, Any]]:
    """Build default config for every pipeline node."""
    return {
        "start": {
            "node_name": "Start",
            "description": "Workflow entry point — triggers the pipeline.",
            "params": {},
        },
        "log_extractor": {
            "node_name": "Extract Monitoring Data",
            "description": "Extracts and segregates raw Azure logs into structured cloud log records.",
            "params": {
                "max_logs": {"value": 500, "type": "number", "label": "Max Logs per Run", "min": 50, "max": 5000},
            },
        },
        "anomaly_detector": {
            "node_name": "Detect Spikes & Anomalies",
            "description": "Uses Gemini to analyze logs for anomalous patterns and errors.",
            "params": {
                "gemini_model": {"value": settings.gemini_model, "type": "text", "label": "Gemini Model"},
                "temperature": {"value": 0.2, "type": "slider", "label": "Temperature", "min": 0.0, "max": 1.0, "step": 0.05},
                "max_output_tokens": {"value": 8192, "type": "number", "label": "Max Output Tokens", "min": 1024, "max": 32768},
            },
        },
        "priority_classifier": {
            "node_name": "Classify & Prioritize",
            "description": "Classifies detected issues into HIGH / MEDIUM / LOW priority levels.",
            "params": {
                "gemini_model": {"value": settings.gemini_model, "type": "text", "label": "Gemini Model"},
                "temperature": {"value": 0.1, "type": "slider", "label": "Temperature", "min": 0.0, "max": 1.0, "step": 0.05},
            },
        },
        "deep_code_analyzer_high": {
            "node_name": "Deep Code Analysis (High)",
            "description": "Deep code-level root cause analysis for HIGH priority incidents.",
            "params": {
                "gemini_model": {"value": settings.gemini_model, "type": "text", "label": "Gemini Model"},
                "temperature": {"value": 0.2, "type": "slider", "label": "Temperature", "min": 0.0, "max": 1.0, "step": 0.05},
                "max_output_tokens": {"value": 8192, "type": "number", "label": "Max Output Tokens", "min": 1024, "max": 32768},
            },
        },
        "deep_code_analyzer_medium": {
            "node_name": "Deep Code Analysis (Medium)",
            "description": "Deep code-level root cause analysis for MEDIUM priority incidents.",
            "params": {
                "gemini_model": {"value": settings.gemini_model, "type": "text", "label": "Gemini Model"},
                "temperature": {"value": 0.2, "type": "slider", "label": "Temperature", "min": 0.0, "max": 1.0, "step": 0.05},
                "max_output_tokens": {"value": 8192, "type": "number", "label": "Max Output Tokens", "min": 1024, "max": 32768},
            },
        },
        "deep_code_analyzer_low": {
            "node_name": "Deep Code Analysis (Low)",
            "description": "Deep code-level root cause analysis for LOW priority incidents.",
            "params": {
                "gemini_model": {"value": settings.gemini_model, "type": "text", "label": "Gemini Model"},
                "temperature": {"value": 0.2, "type": "slider", "label": "Temperature", "min": 0.0, "max": 1.0, "step": 0.05},
                "max_output_tokens": {"value": 8192, "type": "number", "label": "Max Output Tokens", "min": 1024, "max": 32768},
            },
        },
        "high_priority_handler": {
            "node_name": "Solution Architect + Email (High)",
            "description": "Generates solutions and sends critical alert emails for HIGH priority incidents.",
            "params": {
                "email_enabled": {"value": True, "type": "toggle", "label": "Email Notifications"},
                "email_recipient": {"value": settings.smtp_to_email, "type": "text", "label": "Email Recipient"},
                "gemini_model": {"value": settings.gemini_model, "type": "text", "label": "Gemini Model"},
                "temperature": {"value": 0.3, "type": "slider", "label": "Temperature", "min": 0.0, "max": 1.0, "step": 0.05},
            },
        },
        "medium_priority_handler": {
            "node_name": "Solution Architect + Email (Medium)",
            "description": "Generates solutions and sends advisory emails for MEDIUM priority incidents.",
            "params": {
                "email_enabled": {"value": True, "type": "toggle", "label": "Email Notifications"},
                "email_recipient": {"value": settings.smtp_to_email, "type": "text", "label": "Email Recipient"},
                "gemini_model": {"value": settings.gemini_model, "type": "text", "label": "Gemini Model"},
                "temperature": {"value": 0.3, "type": "slider", "label": "Temperature", "min": 0.0, "max": 1.0, "step": 0.05},
            },
        },
        "low_priority_handler": {
            "node_name": "Solution Architect + Email (Low)",
            "description": "Generates solutions and sends informational emails for LOW priority incidents.",
            "params": {
                "email_enabled": {"value": True, "type": "toggle", "label": "Email Notifications"},
                "email_recipient": {"value": settings.smtp_to_email, "type": "text", "label": "Email Recipient"},
                "gemini_model": {"value": settings.gemini_model, "type": "text", "label": "Gemini Model"},
                "temperature": {"value": 0.3, "type": "slider", "label": "Temperature", "min": 0.0, "max": 1.0, "step": 0.05},
            },
        },
        "end": {
            "node_name": "End",
            "description": "Workflow complete — pipeline has finished processing.",
            "params": {},
        },
    }


# In-memory config store (resets on restart)
_node_configs: dict[str, dict[str, Any]] = _default_configs()


class NodeConfigUpdate(BaseModel):
    """Request body for updating node config parameters."""
    params: dict[str, Any]


@router.get("/{node_id}/config")
async def get_node_config(node_id: str):
    """Get the current configuration for a specific node."""
    if node_id not in _node_configs:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    config = _node_configs[node_id]
    return {
        "node_id": node_id,
        "node_name": config["node_name"],
        "description": config["description"],
        "params": config["params"],
    }


@router.put("/{node_id}/config")
async def update_node_config(node_id: str, body: NodeConfigUpdate):
    """Update configuration parameters for a specific node."""
    if node_id not in _node_configs:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")

    config = _node_configs[node_id]

    for key, new_value in body.params.items():
        if key in config["params"]:
            config["params"][key]["value"] = new_value
            logger.info(f"Node '{node_id}': updated {key} = {new_value}")
        else:
            logger.warning(f"Node '{node_id}': unknown param '{key}' ignored")

    return {
        "node_id": node_id,
        "status": "updated",
        "params": config["params"],
    }
