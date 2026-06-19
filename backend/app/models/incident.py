"""
Incident Model - Represents classified and prioritized incidents detected by agents.
"""

import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    String,
    Text,
    Integer,
    Index,
)
from sqlalchemy import JSON

from app.database import Base


class PriorityLevel(str, enum.Enum):
    """Incident priority levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


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
    title = Column(String(500), nullable=False)  # AI-generated incident title
    description = Column(Text, nullable=False)  # Detailed description
    priority = Column(
        Enum(PriorityLevel, name="priority_level"),
        nullable=False,
        index=True,
    )
    category = Column(String(255), nullable=True)  # e.g., "Auth Failure", "Resource Exhaustion"
    status = Column(
        Enum(IncidentStatus, name="incident_status"),
        default=IncidentStatus.OPEN,
        nullable=False,
        index=True,
    )

    # Related log IDs
    log_ids = Column(JSON, nullable=True)  # List of log UUIDs as JSON
    log_count = Column(Integer, default=0)

    # AI Analysis
    ai_analysis = Column(Text, nullable=True)  # Gemini's analysis
    ai_solution = Column(Text, nullable=True)  # Gemini's proposed solution
    ai_model_used = Column(String(100), nullable=True)  # Model version used

    # Email tracking
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    email_recipient = Column(String(255), nullable=True)

    # Agent run reference
    agent_run_id = Column(String(36), nullable=True)

    # Metadata
    raw_data = Column(JSON, nullable=True)  # Extra context
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_incidents_priority_status", "priority", "status"),
        Index("ix_incidents_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Incident {self.id} [{self.priority.value}] {self.title[:50]}>"
