"""
Workflow API Router - Provides real-time workflow state for the frontend visualization.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent_run import AgentRun, AgentRunStatus
from app.schemas.agent_schemas import WorkflowStateResponse, WorkflowNodeState
from app.services.scheduler_service import get_next_run_time

router = APIRouter(prefix="/api/workflow", tags=["Workflow"])

# Define the workflow node structure (matches the React Flow visualization)
WORKFLOW_NODES = [
    {"node_id": "start", "node_name": "Start"},
    {"node_id": "log_extractor", "node_name": "Extract Monitoring Data"},
    {"node_id": "anomaly_detector", "node_name": "Detect Spikes & Anomalies"},
    {"node_id": "priority_classifier", "node_name": "Classify & Prioritize"},
    {"node_id": "deep_code_analyzer_high", "node_name": "Deep Code Analysis (High)"},
    {"node_id": "deep_code_analyzer_medium", "node_name": "Deep Code Analysis (Medium)"},
    {"node_id": "deep_code_analyzer_low", "node_name": "Deep Code Analysis (Low)"},
    {"node_id": "high_priority_handler", "node_name": "Solution Architect + Email (High)"},
    {"node_id": "medium_priority_handler", "node_name": "Solution Architect + Email (Medium)"},
    {"node_id": "low_priority_handler", "node_name": "Solution Architect + Email (Low)"},
    {"node_id": "end", "node_name": "End"},
]


@router.get("/state", response_model=WorkflowStateResponse)
async def get_workflow_state(db: AsyncSession = Depends(get_db)):
    """Get the current workflow state for React Flow visualization."""
    # Get the latest run
    result = await db.execute(
        select(AgentRun).order_by(desc(AgentRun.started_at)).limit(1)
    )
    latest_run = result.scalar_one_or_none()

    is_running = bool(latest_run and latest_run.status == AgentRunStatus.RUNNING)
    current_node = None
    run_id = None
    last_run_at = None

    if latest_run:
        run_id = latest_run.id
        last_run_at = latest_run.started_at
        if is_running and latest_run.run_metadata:
            current_node = latest_run.run_metadata.get("current_agent")

    # Build node states
    nodes = []
    for node_def in WORKFLOW_NODES:
        node_status = "idle"
        if is_running and current_node:
            node_order = [n["node_id"] for n in WORKFLOW_NODES]
            current_idx = node_order.index(current_node) if current_node in node_order else -1
            node_idx = node_order.index(node_def["node_id"])
            if node_idx < current_idx:
                node_status = "completed"
            elif node_idx == current_idx:
                node_status = "running"
        elif latest_run and latest_run.status == AgentRunStatus.SUCCESS:
            node_status = "completed"

        nodes.append(WorkflowNodeState(
            node_id=node_def["node_id"],
            node_name=node_def["node_name"],
            status=node_status,
        ))

    return WorkflowStateResponse(
        run_id=run_id,
        is_running=is_running,
        current_node=current_node,
        nodes=nodes,
        last_run_at=last_run_at,
        next_run_at=get_next_run_time(),
    )
