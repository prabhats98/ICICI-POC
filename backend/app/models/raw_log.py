"""
RawLog Model - Represents raw, unprocessed Azure cloud log entries
that arrive from the external source before segregation.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    String,
    Text,
    Index,
)
from sqlalchemy import JSON

from app.database import Base


class RawLog(Base):
    """Raw Azure cloud log entry before segregation and structuring."""

    __tablename__ = "raw_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ingested_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    source_system = Column(String(255), nullable=True)  # Where the log came from
    raw_payload = Column(JSON, nullable=False)  # The entire raw log as JSON
    raw_text = Column(Text, nullable=True)  # Optional raw text representation
    is_segregated = Column(Boolean, default=False, index=True)  # Has Agent 1 processed it?
    segregated_at = Column(DateTime(timezone=True), nullable=True)
    segregation_run_id = Column(String(36), nullable=True)  # Which pipeline run processed it

    __table_args__ = (
        Index("ix_raw_logs_segregated_ingested", "is_segregated", "ingested_at"),
    )

    def __repr__(self) -> str:
        return f"<RawLog {self.id} segregated={self.is_segregated}>"
