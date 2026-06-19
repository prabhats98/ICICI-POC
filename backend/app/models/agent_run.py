"""
AgentRun Model - Tracks execution history of each agent pipeline run.
"""

import uuid
import enum
from datetime import datetime

# pyrefly: ignore [missing-import]
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
)
# pyrefly: ignore [missing-import]
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
    """Record of a single agent pipeline execution."""

    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_name = Column(String(100), nullable=False)  # Which agent/pipeline ran
    status = Column(
        Enum(AgentRunStatus, name="agent_run_status"),
        default=AgentRunStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Timing
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Metrics
    logs_processed = Column(Integer, default=0)
    incidents_created = Column(Integer, default=0)
    high_priority_count = Column(Integer, default=0)
    medium_priority_count = Column(Integer, default=0)
    low_priority_count = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)

    # Details
    error_message = Column(Text, nullable=True)
    run_metadata = Column(JSON, nullable=True)  # Extra run context
    trigger_type = Column(String(50), default="scheduler")  # "scheduler" or "manual"

    def __repr__(self) -> str:
        return f"<AgentRun {self.id} [{self.status.value}] {self.agent_name}>"
