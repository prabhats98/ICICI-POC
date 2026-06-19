"""
Pydantic schemas for Agent Run API and workflow state.
"""

from datetime import datetime
from uuid import UUID
from typing import Any, Optional

from pydantic import BaseModel

from app.models.agent_run import AgentRunStatus


class AgentRunResponse(BaseModel):
    """Schema for agent run API response."""
    id: UUID
    agent_name: str
    status: AgentRunStatus
    started_at: datetime
    completed_at: Optional[datetime]
    logs_processed: int
    incidents_created: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    emails_sent: int
    error_message: Optional[str]
    trigger_type: str
    metadata: Optional[dict[str, Any]]

    model_config = {"from_attributes": True}


class AgentRunListResponse(BaseModel):
    """Paginated list of agent runs."""
    items: list[AgentRunResponse]
    total: int
    page: int
    page_size: int


class PipelineTriggerRequest(BaseModel):
    """Request to manually trigger the agent pipeline."""
    trigger_type: str = "manual"
    max_logs: int = 100  # Max logs to process in one run


class PipelineTriggerResponse(BaseModel):
    """Response after triggering the pipeline."""
    run_id: UUID
    status: str
    message: str


class WorkflowNodeState(BaseModel):
    """State of a single workflow node."""
    node_id: str
    node_name: str
    status: str  # "idle", "running", "completed", "error"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    items_processed: int = 0
    details: Optional[str] = None


class WorkflowStateResponse(BaseModel):
    """Current state of the entire workflow pipeline."""
    run_id: Optional[UUID]
    is_running: bool
    current_node: Optional[str]
    nodes: list[WorkflowNodeState]
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
