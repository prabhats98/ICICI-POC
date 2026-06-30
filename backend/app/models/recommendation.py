"""
Recommendation Model — Stores structured remediation recommendations for each incident group.
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


class Recommendation(Base):
    """Structured recommendation for an incident group."""

    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_group_id = Column(String(36), nullable=False, index=True)
    incident_id = Column(String(36), nullable=True, index=True)

    # Immediate resolution
    immediate_resolution = Column(Text, nullable=False)
    resolution_steps = Column(JSON, nullable=True)  # List of step-by-step actions

    # Preventive action
    preventive_action = Column(Text, nullable=True)
    preventive_steps = Column(JSON, nullable=True)

    # Priority & impact
    priority = Column(String(20), nullable=False, default="Medium")  # Critical, High, Medium, Low
    business_impact = Column(Text, nullable=True)
    estimated_resolution_minutes = Column(Integer, nullable=True)

    # Ownership
    owner_team = Column(String(255), nullable=True)  # "Infrastructure", "DevOps", "Security", etc.
    escalation_path = Column(String(500), nullable=True)

    # AI metadata
    ai_model_used = Column(String(100), nullable=True)
    generation_method = Column(String(50), nullable=True)  # "rule_based", "ai_generated"

    # Pipeline reference
    agent_run_id = Column(String(36), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_rec_group_priority", "incident_group_id", "priority"),
        Index("ix_rec_owner", "owner_team"),
    )

    def __repr__(self) -> str:
        return f"<Recommendation {self.id} [{self.priority}] team={self.owner_team}>"
