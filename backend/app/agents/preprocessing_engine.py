"""
Agent 2: Preprocessing Engine

Cleans, deduplicates, normalizes timestamps, extracts fields, and writes
raw logs from raw_logs into structured cloud_logs in PostgreSQL.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from app.database import async_session
from app.models.raw_log import RawLog
from app.models.cloud_log import CloudLog
from app.agents.state import PipelineState

logger = logging.getLogger(__name__)

# --- Keyword-based detection rules ---

LEVEL_KEYWORDS = {
    "CRITICAL": ["critical", "fatal", "outage", "downtime", "service unavailable", "503", "crash"],
    "ERROR": ["error", "exception", "failed", "failure", "timeout", "unauthorized", "denied", "refused", "dead letter", "502", "500"],
    "WARNING": ["warning", "warn", "threshold", "exceeded", "approaching", "degraded", "spike", "suspicious", "limit", "429", "throttl"],
    "INFO": ["info", "completed", "deployed", "started", "scaled", "compliant", "backup", "health check passed", "200", "201"],
}

CATEGORY_KEYWORDS = {
    "Security": ["unauthorized", "mfa", "brute force", "firewall", "threat", "access denied", "key vault", "security", "attack", "waf", "block"],
    "Performance": ["dtu", "cpu", "memory", "latency", "throughput", "cache hit", "response time", "timeout", "performance", "slow"],
    "Availability": ["health", "503", "502", "outage", "downtime", "unhealthy", "probe failure", "service unavailable"],
    "Authentication": ["login", "sign-in", "mfa", "authentication", "account lockout", "password", "token"],
    "Network": ["load balancer", "firewall", "syn timeout", "connection", "network", "dns", "routing"],
    "Messaging": ["service bus", "event hub", "dead letter", "queue", "consumer", "ingestion"],
    "Storage": ["storage", "capacity", "blob", "disk", "backup"],
    "Scaling": ["autoscale", "scale out", "scale in", "replica", "container", "scaling"],
    "Deployment": ["deploy", "release", "pipeline", "devops", "ci/cd"],
    "API": ["api management", "gateway", "policy", "rate limit", "throttl", "backend response"],
    "Traffic": ["traffic", "surge", "spike", "request count", "front door", "cdn"],
}

SOURCE_MAPPING = {
    "front door": "Azure Front Door",
    "cdn": "Azure Front Door",
    "application gateway": "Azure Application Gateway",
    "app gateway": "Azure Application Gateway",
    "api management": "Azure API Management",
    "apim": "Azure API Management",
    "virtual machine": "Azure Virtual Machine",
    "vm": "Azure Virtual Machine",
    "sql database": "Azure SQL Database",
    "key vault": "Azure Key Vault",
    "functions": "Azure Functions",
    "storage": "Azure Storage",
    "service bus": "Azure Service Bus",
}


def _detect_level(text: str) -> str:
    text_lower = text.lower()
    for level, keywords in LEVEL_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return level
    return "INFO"


def _detect_category(text: str) -> str:
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "General"


def _detect_source(text: str) -> str:
    text_lower = text.lower()
    for key, source_name in SOURCE_MAPPING.items():
        if key in text_lower:
            return source_name
    return "Azure Unknown Service"


def _preprocess_raw_log(raw_log: RawLog) -> CloudLog:
    """Preprocess a single raw log into a structured CloudLog entry."""
    payload = raw_log.raw_payload or {}
    raw_text = raw_log.raw_text or ""
    source_system = raw_log.source_system or ""

    # Extract message
    message = (
        payload.get("message")
        or payload.get("ResultDescription")
        or payload.get("operationName", "")
        or raw_text
    )
    full_text = f"{message} {raw_text} {source_system} {str(payload)}"

    # Detect level
    level = payload.get("level") or payload.get("Level") or _detect_level(full_text)
    level = level.upper() if level else "INFO"
    if level not in ("CRITICAL", "ERROR", "WARNING", "INFO"):
        level = _detect_level(full_text)

    # Detect category
    category = payload.get("category") or payload.get("Category") or _detect_category(full_text)

    # Detect source — prefer source_system mapping
    source_map = {
        "azure-front-door": "Azure Front Door",
        "azure-app-gateway": "Azure Application Gateway",
        "azure-apim": "Azure API Management",
        "azure-vm": "Azure Virtual Machine",
    }
    source = source_map.get(source_system) or payload.get("source") or _detect_source(full_text)

    # Extract identifiers
    resource_id = payload.get("resourceId") or payload.get("ResourceId") or ""
    resource_group = payload.get("resourceGroup") or payload.get("resource_group") or ""
    subscription_id = payload.get("subscriptionId") or ""
    correlation_id = payload.get("correlationId") or payload.get("correlation_id") or ""
    operation_name = payload.get("operationName") or payload.get("OperationName") or ""

    # Parse timestamp
    timestamp_str = payload.get("timestamp") or payload.get("time") or payload.get("TimeGenerated")
    timestamp = datetime.now(timezone.utc)
    normalized = timestamp
    if timestamp_str:
        try:
            parsed = datetime.fromisoformat(str(timestamp_str).replace("Z", "+00:00"))
            timestamp = parsed
            normalized = parsed.astimezone(timezone.utc)
        except (ValueError, TypeError):
            pass

    return CloudLog(
        id=str(uuid.uuid4()),
        timestamp=timestamp,
        normalized_timestamp=normalized,
        level=level,
        source=source,
        category=category,
        message=str(message)[:5000],
        resource_id=str(resource_id)[:500] if resource_id else None,
        resource_group=str(resource_group)[:255] if resource_group else None,
        subscription_id=str(subscription_id)[:255] if subscription_id else None,
        correlation_id=str(correlation_id)[:255] if correlation_id else None,
        operation_name=str(operation_name)[:500] if operation_name else None,
        raw_data=payload,
        is_processed=False,
        is_duplicate=False,
        created_at=datetime.utcnow(),
    )


async def preprocessing_engine_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Preprocess raw logs into structured cloud_logs.

    Steps:
    1. Read un-preprocessed raw_logs from PostgreSQL
    2. Clean, deduplicate, normalize timestamps, extract fields
    3. Store structured entries in cloud_logs table
    4. Mark raw logs as preprocessed
    """
    logger.info("Agent 2 [Preprocessing Engine]: Starting...")

    try:
        async with async_session() as session:
            # Fetch un-preprocessed raw logs
            query = (
                select(RawLog)
                .where(RawLog.is_preprocessed == False)
                .order_by(RawLog.ingested_at.asc())
                .limit(500)
            )
            result = await session.execute(query)
            raw_logs = result.scalars().all()

            if not raw_logs:
                logger.info("Agent 2 [Preprocessing]: No raw logs to preprocess")
                return {
                    "total_preprocessed": 0,
                    "level_counts": {},
                    "category_counts": {},
                    "cloud_log_ids": [],
                    "duplicates_removed": 0,
                    "current_agent": "preprocessing_engine",
                }

            # Preprocess and deduplicate
            cloud_logs = []
            raw_log_ids = []
            seen_keys = set()
            duplicates = 0
            level_counts = {}
            category_counts = {}

            for raw_log in raw_logs:
                raw_log_ids.append(raw_log.id)
                cloud_log = _preprocess_raw_log(raw_log)

                # Dedup by correlation_id + timestamp (if both exist)
                dedup_key = f"{cloud_log.correlation_id}:{cloud_log.timestamp}"
                if cloud_log.correlation_id and dedup_key in seen_keys:
                    cloud_log.is_duplicate = True
                    duplicates += 1
                    session.add(cloud_log)
                    continue
                seen_keys.add(dedup_key)

                session.add(cloud_log)
                cloud_logs.append(cloud_log)

                # Track stats
                level_counts[cloud_log.level] = level_counts.get(cloud_log.level, 0) + 1
                cat = cloud_log.category or "General"
                category_counts[cat] = category_counts.get(cat, 0) + 1

            # Mark raw logs as preprocessed
            now = datetime.utcnow()
            await session.execute(
                update(RawLog)
                .where(RawLog.id.in_(raw_log_ids))
                .values(is_preprocessed=True, preprocessed_at=now)
            )

            await session.commit()

            cloud_log_ids = [str(log.id) for log in cloud_logs]

            logger.info(
                f"Agent 2 [Preprocessing]: Processed {len(cloud_logs)} logs, "
                f"{duplicates} duplicates removed. "
                f"Levels: {level_counts} | Categories: {category_counts}"
            )

            return {
                "total_preprocessed": len(cloud_logs),
                "level_counts": level_counts,
                "category_counts": category_counts,
                "cloud_log_ids": cloud_log_ids,
                "duplicates_removed": duplicates,
                "current_agent": "preprocessing_engine",
            }

    except Exception as e:
        logger.error(f"Agent 2 [Preprocessing] failed: {e}")
        return {
            "total_preprocessed": 0,
            "level_counts": {},
            "category_counts": {},
            "cloud_log_ids": [],
            "duplicates_removed": 0,
            "errors": [f"Preprocessing failed: {str(e)}"],
            "current_agent": "preprocessing_engine",
        }
