"""
Pydantic schemas for CloudLog API requests and responses.
"""

from datetime import datetime
from uuid import UUID
from typing import Any, Optional

from pydantic import BaseModel, Field


class CloudLogCreate(BaseModel):
    """Schema for creating a new cloud log entry."""
    timestamp: datetime
    level: str = Field(..., pattern="^(INFO|WARNING|ERROR|CRITICAL)$")
    source: str
    category: Optional[str] = None
    message: str
    resource_id: Optional[str] = None
    resource_group: Optional[str] = None
    subscription_id: Optional[str] = None
    correlation_id: Optional[str] = None
    operation_name: Optional[str] = None
    raw_data: Optional[dict[str, Any]] = None


class CloudLogResponse(BaseModel):
    """Schema for cloud log API response."""
    id: UUID
    timestamp: datetime
    level: str
    source: str
    category: Optional[str]
    message: str
    resource_id: Optional[str]
    resource_group: Optional[str]
    subscription_id: Optional[str]
    correlation_id: Optional[str]
    operation_name: Optional[str]
    raw_data: Optional[dict[str, Any]]
    is_processed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CloudLogListResponse(BaseModel):
    """Paginated list of cloud logs."""
    items: list[CloudLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class LogStatsResponse(BaseModel):
    """Aggregated log statistics."""
    total_logs: int
    unprocessed_logs: int
    error_count: int
    warning_count: int
    critical_count: int
    info_count: int
    sources: list[dict[str, Any]]  # [{source: str, count: int}]
    recent_errors: list[CloudLogResponse]
