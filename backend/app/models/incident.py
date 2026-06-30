"""
Incident Model — Classified and prioritized incidents with P1/P2/P3 levels.
"""

import uuid
import enum
from datetime import datetime

from sqlalchemy import Float

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy import JSON

from app.database import Base


class PriorityLevel(str, enum.Enum):
    """Incident priority levels."""
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class IncidentStatus(str, enum.Enum):
    """Incident lifecycle status."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class Incident(Base):
    """Classified incident detected by the agent pipeline."""

    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(
        Enum(PriorityLevel, name="priority_level"),
        nullable=False,
        index=True,
    )
    category = Column(String(255), nullable=True)
    status = Column(
        Enum(IncidentStatus, name="incident_status"),
        default=IncidentStatus.OPEN,
        nullable=False,
        index=True,
    )
    source_service = Column(String(255), nullable=True)  # azure-front-door, azure-app-gateway, etc.

    # Incident group link
    incident_group_id = Column(String(36), nullable=True, index=True)

    # Root cause analysis (denormalized for quick access)
    root_cause = Column(Text, nullable=True)
    root_cause_category = Column(String(255), nullable=True)
    confidence_score = Column(Float, nullable=True)
    affected_component = Column(String(255), nullable=True)  # UI/Frontend, Backend, Network, WAF

    # Structured recommendation (denormalized for quick access)
    immediate_resolution = Column(Text, nullable=True)
    preventive_action = Column(Text, nullable=True)
    business_impact = Column(Text, nullable=True)
    estimated_resolution_minutes = Column(Integer, nullable=True)
    owner_team = Column(String(255), nullable=True)

    # Related log IDs
    log_ids = Column(JSON, nullable=True)
    log_count = Column(Integer, default=0)

    # AI Analysis
    ai_analysis = Column(Text, nullable=True)
    ai_solution = Column(Text, nullable=True)
    ai_model_used = Column(String(100), nullable=True)
    resolution_runbook = Column(Text, nullable=True)

    # Historical context
    historical_match_count = Column(Integer, default=0)
    historical_match_ids = Column(JSON, nullable=True)

    # Email tracking
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    email_recipient = Column(String(255), nullable=True)

    # Resolution tracking
    agent_run_id = Column(String(36), nullable=True)
    resolved_by = Column(String(100), nullable=True)  # "auto" or "manual"
    resolution_duration_minutes = Column(Integer, nullable=True)

    # Metadata
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_incidents_priority_status", "priority", "status"),
        Index("ix_incidents_created_at", "created_at"),
        Index("ix_incidents_source_service", "source_service"),
    )

    def __repr__(self) -> str:
        return f"<Incident {self.id} [{self.priority.value}] {self.title[:50]}>"
