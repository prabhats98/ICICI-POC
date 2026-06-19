"""
RawLog Model — Raw, unprocessed Azure log entries before preprocessing.
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
    """Raw Azure log entry before preprocessing."""

    __tablename__ = "raw_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ingested_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    source_system = Column(String(255), nullable=True)  # azure-front-door, azure-app-gateway, azure-apim, azure-vm
    raw_payload = Column(JSON, nullable=False)
    raw_text = Column(Text, nullable=True)
    is_preprocessed = Column(Boolean, default=False, index=True)
    preprocessed_at = Column(DateTime(timezone=True), nullable=True)
    pipeline_run_id = Column(String(36), nullable=True)

    __table_args__ = (
        Index("ix_raw_logs_preprocessed_ingested", "is_preprocessed", "ingested_at"),
    )

    def __repr__(self) -> str:
        return f"<RawLog {self.id} source={self.source_system} preprocessed={self.is_preprocessed}>"
