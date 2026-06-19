"""
Export API Router - Download analyzed logs and incidents in JSON/CSV/Excel.
"""

from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.cloud_log import CloudLog
from app.models.incident import Incident
from app.services.export_service import export_service

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get("/logs")
async def export_logs(
    format: str = Query("json", pattern="^(json|csv|xlsx)$"),
    db: AsyncSession = Depends(get_db),
):
    """Export all processed logs in the specified format."""
    result = await db.execute(
        select(CloudLog).where(CloudLog.is_processed == True).limit(5000)
    )
    logs = result.scalars().all()

    if not logs:
        raise HTTPException(status_code=404, detail="No processed logs to export")

    data = [
        {
            "id": str(log.id),
            "timestamp": str(log.timestamp),
            "level": log.level,
            "source": log.source,
            "category": log.category,
            "message": log.message,
            "resource_id": log.resource_id,
        }
        for log in logs
    ]

    if format == "json":
        filepath = export_service.export_to_json(data, prefix="logs_export")
    elif format == "csv":
        filepath = export_service.export_to_csv(data, prefix="logs_export")
    else:
        filepath = export_service.export_to_excel(data, prefix="logs_export")

    media_types = {"json": "application/json", "csv": "text/csv", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}

    return FileResponse(
        path=str(filepath),
        filename=filepath.name,
        media_type=media_types[format],
    )


@router.get("/incidents")
async def export_incidents(
    format: str = Query("json", pattern="^(json|csv|xlsx)$"),
    db: AsyncSession = Depends(get_db),
):
    """Export all incidents in the specified format."""
    result = await db.execute(select(Incident).limit(5000))
    incidents = result.scalars().all()

    if not incidents:
        raise HTTPException(status_code=404, detail="No incidents to export")

    data = [
        {
            "id": str(inc.id),
            "title": inc.title,
            "description": inc.description,
            "priority": inc.priority.value if inc.priority else "N/A",
            "category": inc.category,
            "status": inc.status.value if inc.status else "N/A",
            "ai_analysis": inc.ai_analysis,
            "ai_solution": inc.ai_solution,
            "email_sent": inc.email_sent,
            "created_at": str(inc.created_at),
        }
        for inc in incidents
    ]

    filepath = export_service.export_incidents_report(data, format=format)

    media_types = {"json": "application/json", "csv": "text/csv", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}

    return FileResponse(
        path=str(filepath),
        filename=filepath.name,
        media_type=media_types[format],
    )
