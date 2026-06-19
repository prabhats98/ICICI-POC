"""
AgentRun Model — Tracks execution history of each pipeline run.
"""

import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy import JSON

from app.database import Base


class AgentRunStatus(str, enum.Enum):
    """Agent run lifecycle status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentRun(Base):
    """Record of a single pipeline execution."""

    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_name = Column(String(100), nullable=False)
    status = Column(
        Enum(AgentRunStatus, name="agent_run_status"),
        default=AgentRunStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Timing
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Metrics
    logs_processed = Column(Integer, default=0)
    incidents_created = Column(Integer, default=0)
    p1_count = Column(Integer, default=0)
    p2_count = Column(Integer, default=0)
    p3_count = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    retries = Column(Integer, default=0)

    # Details
    error_message = Column(Text, nullable=True)
    run_metadata = Column(JSON, nullable=True)
    trigger_type = Column(String(50), default="scheduler")  # "scheduler" or "manual"
    sources_collected = Column(JSON, nullable=True)  # {"azure-front-door": 50, ...}

    def __repr__(self) -> str:
        return f"<AgentRun {self.id} [{self.status.value}] {self.agent_name}>"
