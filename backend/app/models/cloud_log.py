"""
CloudLog Model — Preprocessed and normalized Azure cloud log entries.
Enhanced with all fields from the pipeline spec.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class CloudLog(Base):
    """Preprocessed Azure cloud log entry with full field extraction."""

    __tablename__ = "cloud_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # --- Core fields ---
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    normalized_timestamp = Column(DateTime(timezone=True), nullable=True)
    level = Column(String(20), nullable=False, index=True)  # INFO, WARNING, ERROR, CRITICAL
    source = Column(String(255), nullable=False, index=True)  # Azure service name
    category = Column(String(255), nullable=True)  # Security, Performance, Availability
    message = Column(Text, nullable=False)

    # --- Azure resource fields ---
    resource_id = Column(String(500), nullable=True)
    resource_name = Column(String(255), nullable=True)
    resource_group = Column(String(255), nullable=True)
    subscription_id = Column(String(255), nullable=True)
    region = Column(String(100), nullable=True)

    # --- Request/Response fields ---
    http_status_code = Column(Integer, nullable=True)
    backend_status = Column(Integer, nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, PUT, etc.
    request_uri = Column(Text, nullable=True)
    client_ip = Column(String(50), nullable=True)
    host = Column(String(500), nullable=True)

    # --- Performance fields ---
    duration_ms = Column(Float, nullable=True)  # Response time in milliseconds
    backend_duration_ms = Column(Float, nullable=True)

    # --- Error fields ---
    error_message = Column(Text, nullable=True)
    exception_details = Column(Text, nullable=True)
    failure_reason = Column(String(500), nullable=True)

    # --- Network/Gateway fields ---
    backend_pool = Column(String(255), nullable=True)
    rule_name = Column(String(255), nullable=True)
    gateway_name = Column(String(255), nullable=True)
    waf_action = Column(String(50), nullable=True)  # Allow, Block, Redirect
    waf_policy = Column(String(255), nullable=True)

    # --- Tracking fields ---
    correlation_id = Column(String(255), nullable=True)
    operation_name = Column(String(500), nullable=True)
    tracking_id = Column(String(255), nullable=True)

    # --- Dedup/Processing ---
    error_fingerprint = Column(String(64), nullable=True, index=True)
    raw_data = Column(JSON, nullable=True)
    is_processed = Column(Boolean, default=False, index=True)
    is_duplicate = Column(Boolean, default=False)

    # --- Classification link ---
    incident_group_id = Column(String(36), nullable=True, index=True)

    # --- Metadata ---
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cloud_logs_level_timestamp", "level", "timestamp"),
        Index("ix_cloud_logs_source_timestamp", "source", "timestamp"),
        Index("ix_cloud_logs_processed_timestamp", "is_processed", "timestamp"),
        Index("ix_cloud_logs_http_status", "http_status_code"),
        Index("ix_cloud_logs_waf_action", "waf_action"),
    )

    def __repr__(self) -> str:
        return f"<CloudLog {self.id} [{self.level}] {self.source}>"
