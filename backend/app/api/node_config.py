"""
Node Config API — Configuration and metadata for individual pipeline nodes.
"""

from fastapi import APIRouter
from app.agents.graph import PIPELINE_NODES, NODE_LABELS

router = APIRouter(prefix="/api/workflow/nodes", tags=["Node Config"])

NODE_DESCRIPTIONS = {
    "log_collector": "Pulls logs from Azure Front Door, Application Gateway, API Management, and VM via Azure Monitor REST API.",
    "preprocessing_engine": "Cleans, deduplicates, normalizes timestamps, extracts fields, and writes structured data to PostgreSQL.",
    "classification_agent": "Sends preprocessed logs to Gemini AI for incident type detection, intent classification, and severity scoring.",
    "priority_agent": "Classifies each detected issue into P1 (critical), P2 (needs attention), or P3 (informational).",
    "context_agent": "Queries PostgreSQL for similar historical incidents and their resolutions to enrich current incidents.",
    "resolution_agent": "Generates AI-powered resolution recommendations and runbooks using Gemini, incorporating historical context.",
    "orchestrator_agent": "Coordinates all agent outputs, aggregates the pipeline summary, and determines notification routing.",
    "notification_agent": "Sends email alerts for P1/P2 incidents via Azure Communication Services or SMTP.",
}


@router.get("/{node_id}/config")
async def get_node_config(node_id: str):
    """Get configuration and metadata for a specific node."""
    if node_id not in PIPELINE_NODES:
        return {"error": f"Unknown node: {node_id}"}

    return {
        "node_id": node_id,
        "label": NODE_LABELS.get(node_id, node_id),
        "description": NODE_DESCRIPTIONS.get(node_id, ""),
        "order": PIPELINE_NODES.index(node_id),
        "params": {},
    }


@router.put("/{node_id}/config")
async def update_node_config(node_id: str, body: dict = {}):
    """Update configuration for a specific node."""
    return {"node_id": node_id, "status": "updated", "params": body.get("params", {})}
