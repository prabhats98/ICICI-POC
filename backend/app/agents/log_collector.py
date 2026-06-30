"""
Agent 1: Log Collector

Pulls logs from Azure Front Door, Application Gateway, API Management, and VM
via the Azure Monitor REST API and stores them in the raw_logs table.
"""

import uuid
import logging
from datetime import datetime
from typing import Any

from app.database import async_session
from app.models.raw_log import RawLog
from app.agents.state import PipelineState
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def log_collector_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Collect logs from Azure Monitor.

    Steps:
    1. Call AzureLogService.collect_all() to pull from all four sources
    2. Store each log entry in the raw_logs table
    3. Return collection stats
    """
    run_id = state.get("run_id", "")
    logger.info("Agent 1 [Log Collector]: Starting Azure log collection...")

    try:
        from app.services.azure_log_service import azure_log_service

        start_date = state.get("start_date")
        end_date = state.get("end_date")

        if start_date and end_date:
            logger.info(f"Agent 1 [Log Collector]: Using custom date range: {start_date} to {end_date}")
            all_logs = await azure_log_service.collect_all(start_date=start_date, end_date=end_date)
        else:
            hours_back = settings.scheduler_interval_hours
            all_logs = await azure_log_service.collect_all(hours_back=hours_back)

        if not any(all_logs.values()):
            logger.info("Agent 1 [Log Collector]: No logs collected from any source")
            return {
                "total_collected": 0,
                "per_source": {},
                "raw_log_ids": [],
                "current_agent": "log_collector",
            }

        # Store raw logs in PostgreSQL
        raw_log_ids = []
        per_source = {}

        async with async_session() as session:
            for source_name, logs in all_logs.items():
                per_source[source_name] = len(logs)
                for log_entry in logs:
                    raw_log = RawLog(
                        id=str(uuid.uuid4()),
                        ingested_at=datetime.utcnow(),
                        source_system=source_name,
                        raw_payload=log_entry.get("raw_payload", log_entry),
                        raw_text=(log_entry.get("message", "") or "")[:5000],
                        is_preprocessed=False,
                        pipeline_run_id=run_id,
                    )
                    session.add(raw_log)
                    raw_log_ids.append(raw_log.id)

            await session.commit()

        total = sum(per_source.values())
        logger.info(
            f"Agent 1 [Log Collector]: Collected {total} logs — "
            + ", ".join(f"{k}: {v}" for k, v in per_source.items())
        )

        return {
            "total_collected": total,
            "per_source": per_source,
            "raw_log_ids": raw_log_ids,
            "current_agent": "log_collector",
        }

    except Exception as e:
        logger.error(f"Agent 1 [Log Collector] failed: {e}")
        return {
            "total_collected": 0,
            "per_source": {},
            "raw_log_ids": [],
            "errors": [f"Log collection failed: {str(e)}"],
            "current_agent": "log_collector",
        }
