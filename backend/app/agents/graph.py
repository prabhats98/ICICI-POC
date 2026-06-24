"""
LangGraph Pipeline — 8-agent linear pipeline for Azure Incident Log analysis.

Flow:
  Log Collector → Preprocessing Engine → Classification Agent → Priority Agent
  → Context Agent → Resolution Agent → Orchestrator Agent → Notification Agent
"""

import time
import uuid
import logging
from datetime import datetime
from typing import Any

import langchain
if not hasattr(langchain, "debug"):
    langchain.debug = False

from langgraph.graph import StateGraph, END

from app.agents.state import PipelineState
from app.agents.log_collector import log_collector_node
from app.agents.preprocessing_engine import preprocessing_engine_node
from app.agents.classification_agent import classification_agent_node
from app.agents.priority_agent import priority_agent_node
from app.agents.context_agent import context_agent_node
from app.agents.resolution_agent import resolution_agent_node
from app.agents.orchestrator_agent import orchestrator_agent_node
from app.agents.notification_agent import notification_agent_node
from app.database import async_session
from app.models.agent_run import AgentRun, AgentRunStatus

logger = logging.getLogger(__name__)

# --- WebSocket broadcast callback ---
_broadcast_callback = None


def set_broadcast_callback(callback):
    """Set the WebSocket broadcast callback from the API layer."""
    global _broadcast_callback
    _broadcast_callback = callback


async def _broadcast(event: str, data: dict):
    """Broadcast a workflow event via WebSocket."""
    if _broadcast_callback:
        try:
            await _broadcast_callback({"event": event, **data})
        except Exception as e:
            logger.warning(f"WebSocket broadcast failed: {e}")


# --- Node timing tracker ---
_node_timings: dict[str, float] = {}

# --- Pipeline node names in execution order ---
PIPELINE_NODES = [
    "log_collector",
    "preprocessing_engine",
    "classification_agent",
    "priority_agent",
    "context_agent",
    "resolution_agent",
    "orchestrator_agent",
    "notification_agent",
]

NODE_LABELS = {
    "log_collector": "Collecting Logs",
    "preprocessing_engine": "Preprocessing",
    "classification_agent": "Classifying Incidents",
    "priority_agent": "Assigning Priority",
    "context_agent": "Looking Up Context",
    "resolution_agent": "Generating Resolutions",
    "orchestrator_agent": "Orchestrating",
    "notification_agent": "Sending Notifications",
}

# --- Wrapper functions with WebSocket broadcasting ---


async def _wrap_node(node_id: str, func, state: PipelineState) -> dict[str, Any]:
    """Generic wrapper that broadcasts start/complete for any node."""
    _node_timings[node_id] = time.time()
    await _broadcast("node_active", {
        "node": node_id,
        "status": "running",
        "input": {"description": NODE_LABELS.get(node_id, node_id)},
    })

    result = await func(state)

    duration = round(time.time() - _node_timings.get(node_id, time.time()), 2)
    await _broadcast("node_complete", {
        "node": node_id,
        "status": "completed",
        "duration": duration,
        "output": _build_output_summary(node_id, result),
    })
    return result


def _build_output_summary(node_id: str, result: dict) -> dict:
    """Build a human-readable output summary for WebSocket broadcast."""
    summaries = {
        "log_collector": lambda r: {
            "description": f"Collected {r.get('total_collected', 0)} logs",
            "per_source": r.get("per_source", {}),
        },
        "preprocessing_engine": lambda r: {
            "description": f"Preprocessed {r.get('total_preprocessed', 0)} logs, {r.get('duplicates_removed', 0)} duplicates removed",
        },
        "classification_agent": lambda r: {
            "description": f"Found {len(r.get('issues_found', []))} issues from {r.get('logs_analyzed', 0)} logs",
        },
        "priority_agent": lambda r: {
            "description": f"P1={len(r.get('p1_incidents', []))}, P2={len(r.get('p2_incidents', []))}, P3={len(r.get('p3_incidents', []))}",
        },
        "context_agent": lambda r: {
            "description": f"Enriched {len(r.get('context_enriched_incidents', []))} incidents with historical context",
        },
        "resolution_agent": lambda r: {
            "description": f"Generated {len(r.get('resolutions', []))} resolutions",
        },
        "orchestrator_agent": lambda r: {
            "description": f"{r.get('summary', {}).get('total_incidents', 0)} incidents, {r.get('summary', {}).get('emails_to_send', 0)} emails queued",
        },
        "notification_agent": lambda r: {
            "description": f"{len(r.get('emails_sent', []))} emails sent, {len(r.get('email_failures', []))} failed",
        },
    }
    builder = summaries.get(node_id, lambda r: {"description": "Completed"})
    return builder(result)


# --- Create wrapper nodes ---

async def _node_log_collector(state): return await _wrap_node("log_collector", log_collector_node, state)
async def _node_preprocessing(state): return await _wrap_node("preprocessing_engine", preprocessing_engine_node, state)
async def _node_classification(state): return await _wrap_node("classification_agent", classification_agent_node, state)
async def _node_priority(state): return await _wrap_node("priority_agent", priority_agent_node, state)
async def _node_context(state): return await _wrap_node("context_agent", context_agent_node, state)
async def _node_resolution(state): return await _wrap_node("resolution_agent", resolution_agent_node, state)
async def _node_orchestrator(state): return await _wrap_node("orchestrator_agent", orchestrator_agent_node, state)
async def _node_notification(state): return await _wrap_node("notification_agent", notification_agent_node, state)


# --- Build the graph ---

def build_pipeline() -> StateGraph:
    """Build the 8-agent linear LangGraph pipeline."""
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("log_collector", _node_log_collector)
    graph.add_node("preprocessing_engine", _node_preprocessing)
    graph.add_node("classification_agent", _node_classification)
    graph.add_node("priority_agent", _node_priority)
    graph.add_node("context_agent", _node_context)
    graph.add_node("resolution_agent", _node_resolution)
    graph.add_node("orchestrator_agent", _node_orchestrator)
    graph.add_node("notification_agent", _node_notification)

    # Linear pipeline — no branching
    graph.set_entry_point("log_collector")
    graph.add_edge("log_collector", "preprocessing_engine")
    graph.add_edge("preprocessing_engine", "classification_agent")
    graph.add_edge("classification_agent", "priority_agent")
    graph.add_edge("priority_agent", "context_agent")
    graph.add_edge("context_agent", "resolution_agent")
    graph.add_edge("resolution_agent", "orchestrator_agent")
    graph.add_edge("orchestrator_agent", "notification_agent")
    graph.add_edge("notification_agent", END)

    return graph


# Compiled graph (singleton)
pipeline = build_pipeline().compile()


async def run_pipeline(
    trigger_type: str = "manual",
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, Any]:
    """
    Execute the full 8-agent pipeline.

    Args:
        trigger_type: "manual" or "scheduler"
        start_time: Optional ISO 8601 GMT start datetime for time-range filtering
        end_time: Optional ISO 8601 GMT end datetime for time-range filtering

    Returns:
        Pipeline result summary
    """
    from app.services.scheduler_service import is_pipeline_enabled

    if not is_pipeline_enabled():
        logger.info("Pipeline is disabled, skipping run")
        return {"status": "disabled", "message": "Pipeline is currently disabled"}

    run_id = str(uuid.uuid4())
    pipeline_start = time.time()
    _node_timings.clear()
    logger.info(f"Pipeline run started: {run_id} (trigger: {trigger_type})")

    # Create AgentRun record
    try:
        async with async_session() as session:
            agent_run = AgentRun(
                id=run_id,
                agent_name="full_pipeline",
                status=AgentRunStatus.RUNNING,
                trigger_type=trigger_type,
                started_at=datetime.utcnow(),
            )
            session.add(agent_run)
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to create AgentRun record: {e}")

    await _broadcast("pipeline_start", {"run_id": run_id, "trigger": trigger_type})

    # Initial state
    has_time_range = bool(start_time and end_time)
    initial_state: PipelineState = {
        "run_id": run_id,
        "trigger_type": trigger_type,
        "started_at": datetime.utcnow().isoformat(),
        "current_agent": "starting",
        "status": "running",
        "time_range_start": start_time or "",
        "time_range_end": end_time or "",
        "no_logs_found": False,
        "total_collected": 0,
        "per_source": {},
        "raw_log_ids": [],
        "total_preprocessed": 0,
        "level_counts": {},
        "category_counts": {},
        "cloud_log_ids": [],
        "duplicates_removed": 0,
        "issues_found": [],
        "has_issues": False,
        "logs_analyzed": 0,
        "classified_issues": [],
        "p1_incidents": [],
        "p2_incidents": [],
        "p3_incidents": [],
        "context_enriched_incidents": [],
        "resolutions": [],
        "summary": {},
        "notifications_to_send": [],
        "emails_sent": [],
        "email_failures": [],
        "export_paths": [],
        "errors": [],
    }

    try:
        result = await pipeline.ainvoke(initial_state)

        total_duration = round(time.time() - pipeline_start, 2)
        summary = result.get("summary", {})

        # Check for no-logs-found when a time range was specified
        no_logs = has_time_range and result.get("total_collected", 0) == 0

        # Update AgentRun record
        try:
            async with async_session() as session:
                from sqlalchemy import update
                await session.execute(
                    update(AgentRun)
                    .where(AgentRun.id == run_id)
                    .values(
                        status=AgentRunStatus.SUCCESS,
                        completed_at=datetime.utcnow(),
                        duration_seconds=total_duration,
                        logs_processed=summary.get("total_preprocessed", 0),
                        incidents_created=summary.get("total_incidents", 0),
                        p1_count=summary.get("p1_count", 0),
                        p2_count=summary.get("p2_count", 0),
                        p3_count=summary.get("p3_count", 0),
                        emails_sent=len(result.get("emails_sent", [])),
                        sources_collected=summary.get("per_source", {}),
                    )
                )
                await session.commit()
        except Exception as e:
            logger.warning(f"Failed to update AgentRun record: {e}")

        await _broadcast("pipeline_complete", {
            "run_id": run_id,
            "status": "completed",
            "duration": total_duration,
            "summary": summary,
            "no_logs_found": no_logs,
        })

        # Broadcast a special event if no logs found for the time range
        if no_logs:
            await _broadcast("pipeline_no_logs", {
                "run_id": run_id,
                "time_range_start": start_time,
                "time_range_end": end_time,
                "message": "No logs found for the selected time range",
            })

        logger.info(f"Pipeline run completed: {run_id} in {total_duration}s")
        return {
            "run_id": run_id,
            "status": "completed",
            "duration": total_duration,
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"Pipeline run failed: {run_id}: {e}")

        try:
            async with async_session() as session:
                from sqlalchemy import update
                await session.execute(
                    update(AgentRun)
                    .where(AgentRun.id == run_id)
                    .values(
                        status=AgentRunStatus.FAILED,
                        completed_at=datetime.utcnow(),
                        duration_seconds=round(time.time() - pipeline_start, 2),
                        error_message=str(e),
                    )
                )
                await session.commit()
        except Exception:
            pass

        await _broadcast("pipeline_error", {"run_id": run_id, "error": str(e)})

        return {"run_id": run_id, "status": "failed", "error": str(e)}
