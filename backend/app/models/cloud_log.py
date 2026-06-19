"""
CloudLog Model — Preprocessed and normalized Azure cloud log entries.
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


class CloudLog(Base):
    """Preprocessed Azure cloud log entry."""

    __tablename__ = "cloud_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    normalized_timestamp = Column(DateTime(timezone=True), nullable=True)
    level = Column(String(20), nullable=False, index=True)  # INFO, WARNING, ERROR, CRITICAL
    source = Column(String(255), nullable=False, index=True)  # Azure service name
    category = Column(String(255), nullable=True)  # Security, Performance, Availability, etc.
    message = Column(Text, nullable=False)
    resource_id = Column(String(500), nullable=True)
    resource_group = Column(String(255), nullable=True)
    subscription_id = Column(String(255), nullable=True)
    correlation_id = Column(String(255), nullable=True)
    operation_name = Column(String(500), nullable=True)
    raw_data = Column(JSON, nullable=True)
    is_processed = Column(Boolean, default=False, index=True)
    is_duplicate = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cloud_logs_level_timestamp", "level", "timestamp"),
        Index("ix_cloud_logs_source_timestamp", "source", "timestamp"),
        Index("ix_cloud_logs_processed_timestamp", "is_processed", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<CloudLog {self.id} [{self.level}] {self.source}>"
