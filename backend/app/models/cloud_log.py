"""
CloudLog Model - Represents Azure cloud log entries stored in PostgreSQL.
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
    """Azure cloud log entry stored in the database."""

    __tablename__ = "cloud_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    level = Column(String(20), nullable=False, index=True)  # INFO, WARNING, ERROR, CRITICAL
    source = Column(String(255), nullable=False, index=True)  # Azure service name
    category = Column(String(255), nullable=True)  # Log category
    message = Column(Text, nullable=False)  # Log message body
    resource_id = Column(String(500), nullable=True)  # Azure resource identifier
    resource_group = Column(String(255), nullable=True)  # Azure resource group
    subscription_id = Column(String(255), nullable=True)  # Azure subscription
    correlation_id = Column(String(255), nullable=True)  # For tracing across services
    operation_name = Column(String(500), nullable=True)  # Azure operation name
    raw_data = Column(JSON, nullable=True)  # Full original log payload
    is_processed = Column(Boolean, default=False, index=True)  # Agent pipeline processed?
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_cloud_logs_level_timestamp", "level", "timestamp"),
        Index("ix_cloud_logs_source_timestamp", "source", "timestamp"),
        Index("ix_cloud_logs_processed_timestamp", "is_processed", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<CloudLog {self.id} [{self.level}] {self.source}>"
