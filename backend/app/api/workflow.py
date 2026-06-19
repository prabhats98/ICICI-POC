"""
Workflow API — Pipeline workflow state for the React Flow visualization.
"""

from fastapi import APIRouter
from app.agents.graph import PIPELINE_NODES, NODE_LABELS

router = APIRouter(prefix="/api/workflow", tags=["Workflow"])


@router.get("/state")
async def get_workflow_state():
    """Get current workflow state for React Flow visualization."""
    return {
        "nodes": [
            {
                "node_id": node_id,
                "label": NODE_LABELS.get(node_id, node_id),
                "status": "idle",
                "order": i,
            }
            for i, node_id in enumerate(PIPELINE_NODES)
        ],
        "pipeline_type": "linear",
        "total_nodes": len(PIPELINE_NODES),
    }
