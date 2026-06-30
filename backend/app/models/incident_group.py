"""
IncidentGroup Model — Groups similar incidents into categories.
Each classified log cluster belongs to one IncidentGroup.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy import JSON

from app.database import Base


class IncidentGroup(Base):
    """Classified incident group — a cluster of similar error patterns."""

    __tablename__ = "incident_groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_name = Column(String(500), nullable=False, index=True)
    error_signature = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)

    # Clustering metadata
    source_service = Column(String(255), nullable=True, index=True)
    http_status_code = Column(String(10), nullable=True)
    error_type = Column(String(255), nullable=True)  # "Backend Timeout", "SSL Error", etc.
    resource_name = Column(String(500), nullable=True)
    operation_name = Column(String(500), nullable=True)

    # Occurrence tracking
    total_occurrences = Column(Integer, default=0)
    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)

    # Related log IDs
    log_ids = Column(JSON, nullable=True)

    # Pipeline run reference
    agent_run_id = Column(String(36), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_ig_category_service", "category_name", "source_service"),
        Index("ix_ig_first_seen", "first_seen"),
        Index("ix_ig_error_type", "error_type"),
    )

    def __repr__(self) -> str:
        return f"<IncidentGroup {self.id} [{self.category_name}] ({self.total_occurrences} events)>"
