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
    status: IncidentStatus
    log_ids: Optional[list[UUID]]
    log_count: int
    ai_analysis: Optional[str]
    ai_solution: Optional[str]
    ai_model_used: Optional[str]
    email_sent: bool
    email_sent_at: Optional[datetime]
    email_recipient: Optional[str]
    agent_run_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}


class IncidentUpdate(BaseModel):
    """Schema for updating an incident."""
    status: Optional[IncidentStatus] = None
    ai_solution: Optional[str] = None
    resolved_at: Optional[datetime] = None


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
    high_priority: int
    medium_priority: int
    low_priority: int
    resolved_today: int
    emails_sent_today: int
