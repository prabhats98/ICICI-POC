"""
Agent 1: Log Extractor & Segregator

Pulls raw logs from the `raw_logs` table, segregates them by level, source,
and category, stores the structured/categorized data into the `cloud_logs`
table in PostgreSQL, and marks the raw logs as processed.

Flow:
  raw_logs (unstructured) → Agent 1 → cloud_logs (segregated & structured)
"""

import uuid
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.raw_log import RawLog
from app.models.cloud_log import CloudLog
from app.agents.state import PipelineState

logger = logging.getLogger(__name__)

# --- Segregation rules for categorizing raw logs ---

LEVEL_KEYWORDS = {
    "CRITICAL": ["critical", "fatal", "outage", "downtime", "service unavailable", "503", "crash"],
    "ERROR": ["error", "exception", "failed", "failure", "timeout", "unauthorized", "denied", "refused", "dead letter"],
    "WARNING": ["warning", "warn", "threshold", "exceeded", "approaching", "degraded", "spike", "suspicious", "limit"],
    "INFO": ["info", "completed", "deployed", "started", "scaled", "compliant", "backup", "health check passed"],
}

CATEGORY_KEYWORDS = {
    "Security": ["unauthorized", "mfa", "brute force", "firewall", "threat", "access denied", "key vault", "security", "attack"],
    "Performance": ["dtu", "cpu", "memory", "latency", "throughput", "cache hit", "response time", "ru/s", "timeout", "performance"],
    "Availability": ["health", "503", "outage", "downtime", "unhealthy", "probe failure", "service unavailable"],
    "Authentication": ["login", "sign-in", "mfa", "authentication", "account lockout", "password"],
    "Network": ["load balancer", "firewall", "syn timeout", "connection", "network", "dns"],
    "Messaging": ["service bus", "event hub", "dead letter", "queue", "consumer", "ingestion"],
    "Storage": ["storage", "capacity", "blob", "disk", "backup"],
    "Scaling": ["autoscale", "scale out", "scale in", "replica", "container", "scaling"],
    "Deployment": ["deploy", "release", "pipeline", "devops", "ci/cd"],
    "Compliance": ["compliance", "policy", "audit", "encryption", "regulation"],
    "Database": ["sql", "cosmos", "replication", "database", "query", "partition"],
    "Runtime": ["function", "out of memory", "runtime", "execution"],
}

SOURCE_MAPPING = {
    "app service": "Azure App Service",
    "sql database": "Azure SQL Database",
    "key vault": "Azure Key Vault",
    "api management": "Azure API Management",
    "functions": "Azure Functions",
    "monitor": "Azure Monitor",
    "storage": "Azure Storage",
    "service bus": "Azure Service Bus",
    "active directory": "Azure Active Directory",
    "devops": "Azure DevOps",
    "cosmos": "Azure Cosmos DB",
    "load balancer": "Azure Load Balancer",
    "backup": "Azure Backup",
    "firewall": "Azure Firewall",
    "event hub": "Azure Event Hub",
    "redis": "Azure Redis Cache",
    "container": "Azure Container Apps",
    "policy": "Azure Policy",
}


def _detect_level(text: str) -> str:
    """Detect log level from raw text content."""
    text_lower = text.lower()
    for level, keywords in LEVEL_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return level
    return "INFO"


def _detect_category(text: str) -> str:
    """Detect log category from raw text content."""
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "General"


def _detect_source(text: str) -> str:
    """Detect Azure service source from raw text content."""
    text_lower = text.lower()
    for key, source_name in SOURCE_MAPPING.items():
        if key in text_lower:
            return source_name
    return "Azure Unknown Service"


def _segregate_raw_log(raw_log: RawLog, run_id: str) -> CloudLog:
    """
    Segregate a single raw log into a structured CloudLog entry.

    Extracts and categorizes:
    - Level (CRITICAL/ERROR/WARNING/INFO)
    - Source (Azure service name)
    - Category (Security, Performance, Availability, etc.)
    - Message, resource IDs, correlation IDs from the payload
    """
    payload = raw_log.raw_payload or {}
    raw_text = raw_log.raw_text or ""

    # Try to extract fields from the JSON payload first
    message = (
        payload.get("message")
        or payload.get("resultDescription")
        or payload.get("operationName", "")
        or raw_text
    )
    full_text = f"{message} {raw_text} {str(payload)}"

    # Segregate by level
    level = payload.get("level") or payload.get("Level") or _detect_level(full_text)
    level = level.upper() if level else "INFO"
    if level not in ("CRITICAL", "ERROR", "WARNING", "INFO"):
        level = _detect_level(full_text)

    # Segregate by category
    category = payload.get("category") or _detect_category(full_text)

    # Segregate by source
    source = (
        payload.get("source")
        or payload.get("resourceProvider")
        or payload.get("Source")
        or _detect_source(full_text)
    )

    # Extract identifiers
    resource_id = payload.get("resourceId") or payload.get("resource_id") or payload.get("ResourceId")
    resource_group = payload.get("resourceGroup") or payload.get("resource_group")
    subscription_id = payload.get("subscriptionId") or payload.get("subscription_id")
    correlation_id = payload.get("correlationId") or payload.get("correlation_id")
    operation_name = payload.get("operationName") or payload.get("operation_name")
    timestamp_str = payload.get("timestamp") or payload.get("time") or payload.get("eventTimestamp")

    # Parse timestamp
    timestamp = datetime.utcnow()
    if timestamp_str:
        try:
            timestamp = datetime.fromisoformat(str(timestamp_str).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            timestamp = datetime.utcnow()

    return CloudLog(
        id=str(uuid.uuid4()),
        timestamp=timestamp,
        level=level,
        source=source,
        category=category,
        message=str(message)[:5000],  # Truncate very long messages
        resource_id=str(resource_id)[:500] if resource_id else None,
        resource_group=str(resource_group)[:255] if resource_group else None,
        subscription_id=str(subscription_id)[:255] if subscription_id else None,
        correlation_id=str(correlation_id)[:255] if correlation_id else None,
        operation_name=str(operation_name)[:500] if operation_name else None,
        raw_data=payload,  # Preserve the full original payload
        is_processed=False,  # Not yet analyzed by Agent 2
        created_at=datetime.utcnow(),
    )


async def _ingest_from_firestore() -> int:
    """
    Fetch unprocessed logs from Firestore and insert them into PostgreSQL raw_logs.

    Returns the number of documents ingested.
    """
    from app.services.firestore_service import firestore_service

    try:
        # Fetch unprocessed docs from Firestore
        firestore_docs = firestore_service.fetch_unprocessed_logs(batch_size=200)

        if not firestore_docs:
            logger.info("Agent 1 [Firestore Ingest]: No new documents in Firestore")
            return 0

        logger.info(
            f"Agent 1 [Firestore Ingest]: Ingesting {len(firestore_docs)} "
            f"documents from Firestore into raw_logs..."
        )

        # Insert into PostgreSQL raw_logs table
        ingested_doc_ids = []
        async with async_session() as session:
            for doc in firestore_docs:
                payload = doc["payload"]
                # Remove the is_ingested tracking field from the payload
                payload_clean = {
                    k: v for k, v in payload.items() if k != "is_ingested"
                }

                # Build a text summary for keyword-based detection
                message = (
                    payload_clean.get("properties", {}).get("message", "")
                    or payload_clean.get("operationName", "")
                    or payload_clean.get("resultType", "")
                )

                raw_log = RawLog(
                    id=str(uuid.uuid4()),
                    ingested_at=datetime.utcnow(),
                    source_system="firestore",
                    raw_payload=payload_clean,
                    raw_text=message[:5000] if message else None,
                    is_segregated=False,
                )
                session.add(raw_log)
                ingested_doc_ids.append(doc["firestore_doc_id"])

            await session.commit()

        # Mark Firestore docs as ingested so they won't be fetched again
        firestore_service.mark_as_ingested(ingested_doc_ids)

        logger.info(
            f"Agent 1 [Firestore Ingest]: Successfully ingested "
            f"{len(ingested_doc_ids)} documents into raw_logs"
        )
        return len(ingested_doc_ids)

    except Exception as e:
        logger.error(f"Agent 1 [Firestore Ingest] failed: {e}")
        return 0


async def log_extractor_node(state: PipelineState) -> dict[str, Any]:
    """
    LangGraph Node: Ingest from Firestore → Segregate → Store in PostgreSQL.

    Steps:
    0. Fetch new logs from Firestore → insert into raw_logs table
    1. Query un-segregated entries from the `raw_logs` table
    2. Segregate each log: detect level, source, category
    3. Store structured entries into the `cloud_logs` table
    4. Mark raw logs as segregated
    5. Return count + segregation summary for the pipeline state
    """
    run_id = state.get("run_id", "")
    logger.info("Agent 1 [Log Extractor]: Starting raw log extraction & segregation...")

    # Step 0: Ingest new logs from Firestore into raw_logs
    firestore_ingested = await _ingest_from_firestore()
    if firestore_ingested > 0:
        logger.info(
            f"Agent 1 [Log Extractor]: Ingested {firestore_ingested} new logs from Firestore"
        )

    try:
        async with async_session() as session:
            # Step 1: Fetch un-segregated raw logs (includes newly ingested Firestore data)
            query = (
                select(RawLog)
                .where(RawLog.is_segregated == False)
                .order_by(RawLog.ingested_at.asc())
                .limit(200)
            )
            result = await session.execute(query)
            raw_logs = result.scalars().all()

            if not raw_logs:
                logger.info("Agent 1 [Log Extractor]: No new raw logs to segregate")
                return {
                    "raw_logs": [],
                    "total_logs_extracted": 0,
                    "segregation_summary": {
                        "total": 0, "critical": 0, "error": 0,
                        "warning": 0, "info": 0, "categories": {},
                    },
                    "has_issues": False,
                    "current_agent": "log_extractor",
                }

            # Step 2 & 3: Segregate each raw log and store as CloudLog
            segregated_logs = []
            raw_log_ids = []
            level_counts = {"CRITICAL": 0, "ERROR": 0, "WARNING": 0, "INFO": 0}
            category_counts = {}

            for raw_log in raw_logs:
                raw_log_ids.append(raw_log.id)

                # Segregate into structured CloudLog
                cloud_log = _segregate_raw_log(raw_log, run_id)
                session.add(cloud_log)
                segregated_logs.append(cloud_log)

                # Track segregation stats
                level_counts[cloud_log.level] = level_counts.get(cloud_log.level, 0) + 1
                cat = cloud_log.category or "General"
                category_counts[cat] = category_counts.get(cat, 0) + 1

            # Step 4: Mark raw logs as segregated
            now = datetime.utcnow()
            await session.execute(
                update(RawLog)
                .where(RawLog.id.in_(raw_log_ids))
                .values(
                    is_segregated=True,
                    segregated_at=now,
                    segregation_run_id=run_id if run_id else None,
                )
            )

            await session.commit()

            # Build segregation summary
            segregation_summary = {
                "total": len(segregated_logs),
                "critical": level_counts.get("CRITICAL", 0),
                "error": level_counts.get("ERROR", 0),
                "warning": level_counts.get("WARNING", 0),
                "info": level_counts.get("INFO", 0),
                "categories": category_counts,
            }

            # Store segregated log IDs for Agent 2 to query from DB
            segregated_ids = [str(log.id) for log in segregated_logs]

            logger.info(
                f"Agent 1 [Log Extractor]: Segregated {len(segregated_logs)} logs → "
                f"CRITICAL={level_counts['CRITICAL']}, ERROR={level_counts['ERROR']}, "
                f"WARNING={level_counts['WARNING']}, INFO={level_counts['INFO']} | "
                f"Categories: {category_counts}"
            )

            return {
                "segregated_log_ids": segregated_ids,
                "total_logs_extracted": len(segregated_logs),
                "segregation_summary": segregation_summary,
                "current_agent": "log_extractor",
            }

    except Exception as e:
        logger.error(f"Agent 1 [Log Extractor] failed: {e}")
        return {
            "segregated_log_ids": [],
            "total_logs_extracted": 0,
            "segregation_summary": {},
            "errors": [f"Log extraction & segregation failed: {str(e)}"],
            "current_agent": "log_extractor",
        }
