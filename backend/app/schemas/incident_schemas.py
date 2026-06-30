"""
Pydantic schemas for Incident API requests and responses.
"""

from datetime import datetime
from uuid import UUID
from typing import Any, Optional

from pydantic import BaseModel

from app.models.incident import PriorityLevel, IncidentStatus


class IncidentCreate(BaseModel):
    """Schema for creating a new incident (internal use by agents)."""
    title: str
    description: str
    priority: PriorityLevel
    category: Optional[str] = None
    source_service: Optional[str] = None
    log_ids: Optional[list[UUID]] = None
    log_count: int = 0
    ai_analysis: Optional[str] = None
    ai_solution: Optional[str] = None
    ai_model_used: Optional[str] = None
    agent_run_id: Optional[UUID] = None
    raw_data: Optional[dict[str, Any]] = None


class IncidentResponse(BaseModel):
    """Schema for incident API response."""
    id: UUID
    title: str
    description: str
    priority: PriorityLevel
    category: Optional[str]
    source_service: Optional[str] = None
    status: IncidentStatus
    log_ids: Optional[list[UUID]] = None
    log_count: int = 0

    # AI analysis
    ai_analysis: Optional[str] = None
    ai_solution: Optional[str] = None
    resolution_runbook: Optional[str] = None
    ai_model_used: Optional[str] = None

    # RCA fields
    incident_group_id: Optional[str] = None
    root_cause: Optional[str] = None
    root_cause_category: Optional[str] = None
    confidence_score: Optional[float] = None
    affected_component: Optional[str] = None

    # Recommendation fields
    immediate_resolution: Optional[str] = None
    preventive_action: Optional[str] = None
    business_impact: Optional[str] = None
    estimated_resolution_minutes: Optional[int] = None
    owner_team: Optional[str] = None

    # Tracking
    historical_match_count: int = 0
    email_sent: bool = False
    email_sent_at: Optional[datetime] = None
    email_recipient: Optional[str] = None
    agent_run_id: Optional[UUID] = None
    resolved_by: Optional[str] = None
    resolution_duration_minutes: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IncidentUpdate(BaseModel):
    """Schema for updating an incident."""
    status: Optional[IncidentStatus] = None
    ai_solution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class IncidentListResponse(BaseModel):
    """Paginated list of incidents."""
    items: list[IncidentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class IncidentStatsResponse(BaseModel):
    """Incident statistics for dashboard."""
    total_incidents: int
    open_incidents: int
    p1_count: int
    p2_count: int
    p3_count: int
    resolved_today: int
    emails_sent_today: int
