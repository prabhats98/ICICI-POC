"""
Logs API Router - CRUD operations for cloud log entries.
"""

import math
from uuid import UUID
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.cloud_log import CloudLog
from app.schemas.log_schemas import (
    CloudLogCreate,
    CloudLogResponse,
    CloudLogListResponse,
    LogStatsResponse,
)

router = APIRouter(prefix="/api/logs", tags=["Logs"])


@router.get("/", response_model=CloudLogListResponse)
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: Optional[str] = Query(None, pattern="^(INFO|WARNING|ERROR|CRITICAL)$"),
    source: Optional[str] = None,
    is_processed: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List cloud logs with pagination and filters."""
    query = select(CloudLog)
    count_query = select(func.count(CloudLog.id))

    # Apply filters
    if level:
        query = query.where(CloudLog.level == level)
        count_query = count_query.where(CloudLog.level == level)
    if source:
        query = query.where(CloudLog.source.ilike(f"%{source}%"))
        count_query = count_query.where(CloudLog.source.ilike(f"%{source}%"))
    if is_processed is not None:
        query = query.where(CloudLog.is_processed == is_processed)
        count_query = count_query.where(CloudLog.is_processed == is_processed)
    if start_date:
        query = query.where(CloudLog.timestamp >= start_date)
        count_query = count_query.where(CloudLog.timestamp >= start_date)
    if end_date:
        query = query.where(CloudLog.timestamp <= end_date)
        count_query = count_query.where(CloudLog.timestamp <= end_date)
    if search:
        query = query.where(CloudLog.message.ilike(f"%{search}%"))
        count_query = count_query.where(CloudLog.message.ilike(f"%{search}%"))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(CloudLog.timestamp)).offset(offset).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return CloudLogListResponse(
        items=[CloudLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/stats", response_model=LogStatsResponse)
async def get_log_stats(db: AsyncSession = Depends(get_db)):
    """Get aggregated log statistics for the dashboard."""
    # Total counts
    total = (await db.execute(select(func.count(CloudLog.id)))).scalar() or 0
    unprocessed = (await db.execute(
        select(func.count(CloudLog.id)).where(CloudLog.is_processed == False)
    )).scalar() or 0

    # Level counts
    error_count = (await db.execute(
        select(func.count(CloudLog.id)).where(CloudLog.level == "ERROR")
    )).scalar() or 0
    warning_count = (await db.execute(
        select(func.count(CloudLog.id)).where(CloudLog.level == "WARNING")
    )).scalar() or 0
    critical_count = (await db.execute(
        select(func.count(CloudLog.id)).where(CloudLog.level == "CRITICAL")
    )).scalar() or 0
    info_count = (await db.execute(
        select(func.count(CloudLog.id)).where(CloudLog.level == "INFO")
    )).scalar() or 0

    # Sources breakdown
    source_query = (
        select(CloudLog.source, func.count(CloudLog.id).label("count"))
        .group_by(CloudLog.source)
        .order_by(desc("count"))
        .limit(10)
    )
    source_result = await db.execute(source_query)
    sources = [{"source": row.source, "count": row.count} for row in source_result]

    # Recent errors
    recent_errors_query = (
        select(CloudLog)
        .where(CloudLog.level.in_(["ERROR", "CRITICAL"]))
        .order_by(desc(CloudLog.timestamp))
        .limit(5)
    )
    recent_result = await db.execute(recent_errors_query)
    recent_errors = [CloudLogResponse.model_validate(log) for log in recent_result.scalars()]

    return LogStatsResponse(
        total_logs=total,
        unprocessed_logs=unprocessed,
        error_count=error_count,
        warning_count=warning_count,
        critical_count=critical_count,
        info_count=info_count,
        sources=sources,
        recent_errors=recent_errors,
    )


@router.get("/{log_id}", response_model=CloudLogResponse)
async def get_log(log_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single log entry by ID."""
    result = await db.execute(select(CloudLog).where(CloudLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return CloudLogResponse.model_validate(log)


@router.post("/", response_model=CloudLogResponse, status_code=201)
async def create_log(log_data: CloudLogCreate, db: AsyncSession = Depends(get_db)):
    """Create a new cloud log entry (for testing/ingestion)."""
    log = CloudLog(**log_data.model_dump())
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return CloudLogResponse.model_validate(log)


@router.post("/bulk", response_model=dict, status_code=201)
async def create_logs_bulk(
    logs: list[CloudLogCreate],
    db: AsyncSession = Depends(get_db),
):
    """Bulk create cloud log entries."""
    db_logs = [CloudLog(**log_data.model_dump()) for log_data in logs]
    db.add_all(db_logs)
    await db.flush()
    return {"created": len(db_logs), "message": f"Successfully created {len(db_logs)} log entries"}
