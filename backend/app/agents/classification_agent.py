"""
Agent 3: Classification Agent

Reads preprocessed cloud_logs from PostgreSQL, sends them to Gemini for
incident type detection, intent classification, and severity scoring.
"""

import logging
from typing import Any

from sqlalchemy import select, update

from app.database import async_session
from app.models.cloud_log import CloudLog
from app.agents.state import PipelineState
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


async def classification_agent_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Classify preprocessed logs for incidents.

    Steps:
    1. Query unprocessed cloud_logs from DB
    2. Send structured data to Gemini for classification
    3. Mark logs as processed
    4. Return detected issues
    """
    logger.info("Agent 3 [Classification]: Starting log classification...")

    try:
        async with async_session() as session:
            cloud_log_ids = state.get("cloud_log_ids", [])

            if cloud_log_ids:
                query = select(CloudLog).where(CloudLog.id.in_(cloud_log_ids))
            else:
                query = (
                    select(CloudLog)
                    .where(CloudLog.is_processed == False)
                    .where(CloudLog.is_duplicate == False)
                    .order_by(CloudLog.timestamp.desc())
                    .limit(200)
                )

            result = await session.execute(query)
            db_logs = result.scalars().all()

            if not db_logs:
                logger.info("Agent 3 [Classification]: No logs to classify")
                return {
                    "issues_found": [],
                    "has_issues": False,
                    "logs_analyzed": 0,
                    "current_agent": "classification_agent",
                }

            # Prepare structured data for Gemini
            structured_logs = []
            log_ids = []
            for log in db_logs:
                log_ids.append(log.id)
                structured_logs.append({
                    "id": str(log.id),
                    "timestamp": str(log.timestamp),
                    "level": log.level,
                    "source": log.source,
                    "category": log.category,
                    "message": log.message,
                    "resource_id": log.resource_id,
                    "resource_group": log.resource_group,
                    "correlation_id": log.correlation_id,
                    "operation_name": log.operation_name,
                })

            logger.info(f"Agent 3 [Classification]: Sending {len(structured_logs)} logs to Gemini")

            # Classify with Gemini
            analysis_result = await gemini_service.classify_logs(structured_logs)
            issues = analysis_result.get("issues", [])
            has_issues = len(issues) > 0

            # Mark logs as processed
            await session.execute(
                update(CloudLog)
                .where(CloudLog.id.in_(log_ids))
                .values(is_processed=True)
            )
            await session.commit()

            logger.info(f"Agent 3 [Classification]: Found {len(issues)} issues from {len(structured_logs)} logs")

            return {
                "issues_found": issues,
                "has_issues": has_issues,
                "logs_analyzed": len(structured_logs),
                "current_agent": "classification_agent",
            }

    except Exception as e:
        logger.error(f"Agent 3 [Classification] failed: {e}")
        return {
            "issues_found": [],
            "has_issues": False,
            "logs_analyzed": 0,
            "errors": [f"Classification failed: {str(e)}"],
            "current_agent": "classification_agent",
        }
