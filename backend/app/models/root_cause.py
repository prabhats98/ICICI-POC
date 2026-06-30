"""
RootCauseAnalysis Model — Stores AI-generated root cause analysis for each incident group.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy import JSON

from app.database import Base


class RootCauseAnalysis(Base):
    """Root cause analysis for an incident group."""

    __tablename__ = "root_cause_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_group_id = Column(String(36), nullable=False, index=True)
    incident_id = Column(String(36), nullable=True, index=True)

    # Root cause details
    root_cause = Column(Text, nullable=False)
    root_cause_category = Column(String(255), nullable=True)  # "Backend Timeout", "SSL Expired", etc.
    confidence_score = Column(Float, default=0.0)  # 0.0 to 1.0

    # Evidence
    evidence = Column(JSON, nullable=True)  # List of evidence items
    evidence_summary = Column(Text, nullable=True)
    supporting_log_ids = Column(JSON, nullable=True)  # Log IDs that support this RCA
    supporting_log_count = Column(Integer, default=0)

    # Historical matching
    similar_historical_count = Column(Integer, default=0)
    similar_historical_ids = Column(JSON, nullable=True)

    # Component affected
    affected_component = Column(String(255), nullable=True)  # "UI/Frontend", "Backend", "Network", etc.
    affected_resource = Column(String(500), nullable=True)

    # AI metadata
    ai_model_used = Column(String(100), nullable=True)
    analysis_method = Column(String(50), nullable=True)  # "rule_based", "ai_analysis", "pattern_match"

    # Pipeline reference
    agent_run_id = Column(String(36), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_rca_group_confidence", "incident_group_id", "confidence_score"),
        Index("ix_rca_category", "root_cause_category"),
    )

    def __repr__(self) -> str:
        return f"<RCA {self.id} [{self.root_cause_category}] confidence={self.confidence_score}>"
