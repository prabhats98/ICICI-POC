"""
Incidents API Router - CRUD operations for classified incidents.
"""

import math
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.incident import Incident, PriorityLevel, IncidentStatus
from app.schemas.incident_schemas import (
    IncidentResponse,
    IncidentUpdate,
    IncidentListResponse,
    IncidentStatsResponse,
)

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])


@router.get("/", response_model=IncidentListResponse)
async def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    priority: Optional[PriorityLevel] = None,
    status: Optional[IncidentStatus] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List incidents with pagination and filters."""
    query = select(Incident)
    count_query = select(func.count(Incident.id))

    if priority:
        query = query.where(Incident.priority == priority)
        count_query = count_query.where(Incident.priority == priority)
    if status:
        query = query.where(Incident.status == status)
        count_query = count_query.where(Incident.status == status)
    if category:
        query = query.where(Incident.category.ilike(f"%{category}%"))
        count_query = count_query.where(Incident.category.ilike(f"%{category}%"))
    if search:
        query = query.where(Incident.title.ilike(f"%{search}%"))
        count_query = count_query.where(Incident.title.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(desc(Incident.created_at)).offset(offset).limit(page_size)

    result = await db.execute(query)
    incidents = result.scalars().all()

    return IncidentListResponse(
        items=[IncidentResponse.model_validate(inc) for inc in incidents],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/stats", response_model=IncidentStatsResponse)
async def get_incident_stats(db: AsyncSession = Depends(get_db)):
    """Get incident statistics for the dashboard."""
    total = (await db.execute(select(func.count(Incident.id)))).scalar() or 0
    open_count = (await db.execute(
        select(func.count(Incident.id)).where(Incident.status == IncidentStatus.OPEN)
    )).scalar() or 0

    high = (await db.execute(
        select(func.count(Incident.id)).where(Incident.priority == PriorityLevel.HIGH)
    )).scalar() or 0
    medium = (await db.execute(
        select(func.count(Incident.id)).where(Incident.priority == PriorityLevel.MEDIUM)
    )).scalar() or 0
    low = (await db.execute(
        select(func.count(Incident.id)).where(Incident.priority == PriorityLevel.LOW)
    )).scalar() or 0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = (await db.execute(
        select(func.count(Incident.id)).where(
            and_(
                Incident.status == IncidentStatus.RESOLVED,
                Incident.resolved_at >= today_start,
            )
        )
    )).scalar() or 0

    emails_today = (await db.execute(
        select(func.count(Incident.id)).where(
            and_(
                Incident.email_sent == True,
                Incident.email_sent_at >= today_start,
            )
        )
    )).scalar() or 0

    return IncidentStatsResponse(
        total_incidents=total,
        open_incidents=open_count,
        high_priority=high,
        medium_priority=medium,
        low_priority=low,
        resolved_today=resolved_today,
        emails_sent_today=emails_today,
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single incident with full details."""
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return IncidentResponse.model_validate(incident)


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: UUID,
    update_data: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an incident (e.g., change status to RESOLVED)."""
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    if "status" in update_dict and update_dict["status"] == IncidentStatus.RESOLVED:
        update_dict["resolved_at"] = datetime.utcnow()

    for field, value in update_dict.items():
        setattr(incident, field, value)

    await db.flush()
    await db.refresh(incident)
    return IncidentResponse.model_validate(incident)
