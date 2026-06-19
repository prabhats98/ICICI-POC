"""
Agent 2: Anomaly Detector

Reads the **segregated logs from PostgreSQL** (stored by Agent 1),
sends them to Gemini 2.5 Flash for analysis, and exports results.

Flow:
  cloud_logs (PostgreSQL) → Agent 2 → Gemini analysis → JSON/CSV/Excel export
"""

import logging
from typing import Any

from sqlalchemy import select, update

from app.database import async_session
from app.models.cloud_log import CloudLog
from app.agents.state import PipelineState
from app.services.gemini_service import gemini_service
from app.services.export_service import export_service

logger = logging.getLogger(__name__)


async def anomaly_detector_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Read segregated logs from DB → Analyze with Gemini.

    Steps:
    1. Query un-analyzed (is_processed=False) logs from `cloud_logs` table
       (these were just stored by Agent 1 after segregation)
    2. Send the structured, categorized data to Gemini 2.5 Flash
    3. Export analysis results to JSON/CSV/Excel
    4. Mark logs as processed in the DB
    5. Pass detected issues to Agent 3
    """
    segregated_ids = state.get("segregated_log_ids", [])
    total_extracted = state.get("total_logs_extracted", 0)
    logger.info(f"Agent 2 [Anomaly Detector]: Reading {total_extracted} segregated logs from PostgreSQL...")

    try:
        async with async_session() as session:
            # Step 1: Read segregated logs from PostgreSQL
            # If we have specific IDs from Agent 1, use those; otherwise get unprocessed
            if segregated_ids:
                import uuid as uuid_mod
                id_list = [uuid_mod.UUID(sid) for sid in segregated_ids]
                query = select(CloudLog).where(CloudLog.id.in_(id_list))
            else:
                query = (
                    select(CloudLog)
                    .where(CloudLog.is_processed == False)
                    .order_by(CloudLog.timestamp.desc())
                    .limit(200)
                )

            result = await session.execute(query)
            db_logs = result.scalars().all()

            if not db_logs:
                logger.info("Agent 2 [Anomaly Detector]: No segregated logs to analyze")
                return {
                    "analysis_result": {},
                    "issues_found": [],
                    "has_issues": False,
                    "current_agent": "anomaly_detector",
                }

            # Step 2: Prepare structured data from PostgreSQL for Gemini
            # The data is already segregated by Agent 1 — we send categorized, structured data
            structured_logs = []
            log_ids = []
            for log in db_logs:
                log_ids.append(log.id)
                structured_logs.append({
                    "id": str(log.id),
                    "timestamp": str(log.timestamp),
                    "level": log.level,  # Already segregated by Agent 1
                    "source": log.source,  # Already segregated by Agent 1
                    "category": log.category,  # Already segregated by Agent 1
                    "message": log.message,
                    "resource_id": log.resource_id,
                    "resource_group": log.resource_group,
                    "correlation_id": log.correlation_id,
                    "operation_name": log.operation_name,
                })

            # Build a summary of the segregated data for better Gemini analysis
            level_distribution = {}
            category_distribution = {}
            source_distribution = {}
            for log_entry in structured_logs:
                lvl = log_entry["level"]
                cat = log_entry.get("category", "General")
                src = log_entry.get("source", "Unknown")
                level_distribution[lvl] = level_distribution.get(lvl, 0) + 1
                category_distribution[cat] = category_distribution.get(cat, 0) + 1
                source_distribution[src] = source_distribution.get(src, 0) + 1

            logger.info(
                f"Agent 2 [Anomaly Detector]: Sending {len(structured_logs)} segregated logs "
                f"to Gemini. Distribution — Levels: {level_distribution}, "
                f"Categories: {category_distribution}"
            )

            # Step 3: Send segregated data to Gemini for deep analysis
            analysis_result = await gemini_service.analyze_logs(structured_logs)
            issues = analysis_result.get("issues", [])
            has_issues = len(issues) > 0

            # Step 4: Export analysis results
            export_paths = []
            if issues:
                try:
                    json_path = export_service.export_to_json(issues, prefix="anomaly_analysis")
                    csv_path = export_service.export_to_csv(issues, prefix="anomaly_analysis")
                    excel_path = export_service.export_to_excel(issues, prefix="anomaly_analysis")
                    export_paths = [str(json_path), str(csv_path), str(excel_path)]
                except Exception as export_err:
                    logger.warning(f"Export failed (non-critical): {export_err}")

            # Step 5: Mark logs as processed in PostgreSQL
            await session.execute(
                update(CloudLog)
                .where(CloudLog.id.in_(log_ids))
                .values(is_processed=True)
            )
            await session.commit()

            logger.info(
                f"Agent 2 [Anomaly Detector]: Analysis complete. "
                f"Found {len(issues)} issues from {len(structured_logs)} segregated logs. "
                f"Exported to {len(export_paths)} files."
            )

            return {
                "analysis_result": analysis_result,
                "issues_found": issues,
                "has_issues": has_issues,
                "export_paths": export_paths,
                "level_distribution": level_distribution,
                "category_distribution": category_distribution,
                "current_agent": "anomaly_detector",
            }

    except Exception as e:
        logger.error(f"Agent 2 [Anomaly Detector] failed: {e}")
        return {
            "analysis_result": {},
            "issues_found": [],
            "has_issues": False,
            "errors": [f"Anomaly detection failed: {str(e)}"],
            "current_agent": "anomaly_detector",
        }
