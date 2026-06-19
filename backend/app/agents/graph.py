"""
LangGraph Pipeline - Builds and runs the multi-agent state graph.

Data Flow (PostgreSQL-centric):
  raw_logs (DB)
    → Agent 1: Segregate → cloud_logs (DB, structured & categorized)
    → Agent 2: Read from DB → Gemini analysis
    → Agent 3: Classify priority → Incident records (DB)
    → Agent 4a/4b/4c: Handle by priority → Email / Solution / Log
"""

import uuid
import logging
from datetime import datetime
from typing import Any

from langgraph.graph import StateGraph, END

from app.agents.state import PipelineState
from app.agents.log_extractor import log_extractor_node
from app.agents.anomaly_detector import anomaly_detector_node
from app.agents.priority_classifier import priority_classifier_node
from app.agents.high_priority_handler import high_priority_handler_node
from app.agents.medium_priority_handler import medium_priority_handler_node
from app.agents.low_priority_handler import low_priority_handler_node
from app.agents.deep_code_analyzer import (
    deep_code_analyzer_high_node,
    deep_code_analyzer_medium_node,
    deep_code_analyzer_low_node,
)
from app.database import async_session
from app.models.agent_run import AgentRun, AgentRunStatus

logger = logging.getLogger(__name__)

# --- WebSocket broadcast callback (set by the API layer) ---
_broadcast_callback = None


def set_broadcast_callback(callback):
    """Set the WebSocket broadcast callback from the API layer."""
    global _broadcast_callback
    _broadcast_callback = callback


async def _broadcast(event: str, data: dict):
    """Broadcast a workflow event via WebSocket if callback is set."""
    if _broadcast_callback:
        try:
            await _broadcast_callback({"event": event, **data})
        except Exception as e:
            logger.warning(f"WebSocket broadcast failed: {e}")


# --- Wrapper nodes that broadcast status ---

async def _extract_node(state: PipelineState) -> dict[str, Any]:
    await _broadcast("node_active", {"node": "log_extractor", "status": "running"})
    result = await log_extractor_node(state)
    summary = result.get("segregation_summary", {})
    await _broadcast("node_complete", {
        "node": "log_extractor",
        "status": "completed",
        "logs_extracted": result.get("total_logs_extracted", 0),
        "segregation": summary,
    })
    return result


async def _detect_node(state: PipelineState) -> dict[str, Any]:
    await _broadcast("node_active", {"node": "anomaly_detector", "status": "running"})
    result = await anomaly_detector_node(state)
    await _broadcast("node_complete", {"node": "anomaly_detector", "status": "completed", "issues_found": len(result.get("issues_found", []))})
    return result


async def _classify_node(state: PipelineState) -> dict[str, Any]:
    await _broadcast("node_active", {"node": "priority_classifier", "status": "running"})
    result = await priority_classifier_node(state)
    await _broadcast("node_complete", {
        "node": "priority_classifier",
        "status": "completed",
        "high": len(result.get("high_priority_incidents", [])),
        "medium": len(result.get("medium_priority_incidents", [])),
        "low": len(result.get("low_priority_incidents", [])),
    })
    return result


async def _high_node(state: PipelineState) -> dict[str, Any]:
    await _broadcast("node_active", {"node": "high_priority_handler", "status": "running"})
    result = await high_priority_handler_node(state)
    await _broadcast("node_complete", {"node": "high_priority_handler", "status": "completed", "emails_sent": len(result.get("emails_sent", []))})
    return result


async def _medium_node(state: PipelineState) -> dict[str, Any]:
    await _broadcast("node_active", {"node": "medium_priority_handler", "status": "running"})
    result = await medium_priority_handler_node(state)
    await _broadcast("node_complete", {"node": "medium_priority_handler", "status": "completed", "solutions": len(result.get("medium_priority_solutions", []))})
    return result


async def _low_node(state: PipelineState) -> dict[str, Any]:
    await _broadcast("node_active", {"node": "low_priority_handler", "status": "running"})
    result = await low_priority_handler_node(state)
    await _broadcast("node_complete", {"node": "low_priority_handler", "status": "completed", "logged": result.get("low_priority_logged", 0)})
    return result


# --- Deep Code Analyzer wrapper nodes ---

async def _deep_analyze_high_node(state: PipelineState) -> dict[str, Any]:
    await _broadcast("node_active", {"node": "deep_code_analyzer_high", "status": "running"})
    result = await deep_code_analyzer_high_node(state)
    await _broadcast("node_complete", {
        "node": "deep_code_analyzer_high",
        "status": "completed",
        "analyses": len(result.get("deep_analysis_high", [])),
    })
    return result


async def _deep_analyze_medium_node(state: PipelineState) -> dict[str, Any]:
    await _broadcast("node_active", {"node": "deep_code_analyzer_medium", "status": "running"})
    result = await deep_code_analyzer_medium_node(state)
    await _broadcast("node_complete", {
        "node": "deep_code_analyzer_medium",
        "status": "completed",
        "analyses": len(result.get("deep_analysis_medium", [])),
    })
    return result


async def _deep_analyze_low_node(state: PipelineState) -> dict[str, Any]:
    await _broadcast("node_active", {"node": "deep_code_analyzer_low", "status": "running"})
    result = await deep_code_analyzer_low_node(state)
    await _broadcast("node_complete", {
        "node": "deep_code_analyzer_low",
        "status": "completed",
        "analyses": len(result.get("deep_analysis_low", [])),
    })
    return result


# --- Routing logic ---

def should_continue_after_extraction(state: PipelineState) -> str:
    """After extraction & segregation, check if there are logs to analyze."""
    if state.get("total_logs_extracted", 0) > 0:
        return "anomaly_detector"
    return END


def route_after_classification(state: PipelineState) -> str:
    """After classification, route to deep analysis based on detected priorities."""
    has_high = len(state.get("high_priority_incidents", [])) > 0
    has_medium = len(state.get("medium_priority_incidents", [])) > 0

    if has_high:
        return "deep_code_analyzer_high"
    elif has_medium:
        return "deep_code_analyzer_medium"
    else:
        return "deep_code_analyzer_low"


def route_after_high(state: PipelineState) -> str:
    """After high priority, check if medium needs handling."""
    if len(state.get("medium_priority_incidents", [])) > 0:
        return "deep_code_analyzer_medium"
    elif len(state.get("low_priority_incidents", [])) > 0:
        return "deep_code_analyzer_low"
    return END


def route_after_medium(state: PipelineState) -> str:
    """After medium priority, check if low needs handling."""
    if len(state.get("low_priority_incidents", [])) > 0:
        return "deep_code_analyzer_low"
    return END


# --- Build the graph ---

def build_pipeline() -> StateGraph:
    """Build the LangGraph multi-agent pipeline."""
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("log_extractor", _extract_node)
    graph.add_node("anomaly_detector", _detect_node)
    graph.add_node("priority_classifier", _classify_node)
    graph.add_node("deep_code_analyzer_high", _deep_analyze_high_node)
    graph.add_node("deep_code_analyzer_medium", _deep_analyze_medium_node)
    graph.add_node("deep_code_analyzer_low", _deep_analyze_low_node)
    graph.add_node("high_priority_handler", _high_node)
    graph.add_node("medium_priority_handler", _medium_node)
    graph.add_node("low_priority_handler", _low_node)

    # Set entry point
    graph.set_entry_point("log_extractor")

    # Add edges
    graph.add_conditional_edges(
        "log_extractor",
        should_continue_after_extraction,
        {
            "anomaly_detector": "anomaly_detector",
            END: END,
        },
    )

    graph.add_edge("anomaly_detector", "priority_classifier")

    # Classifier routes to deep analysis nodes first
    graph.add_conditional_edges(
        "priority_classifier",
        route_after_classification,
        {
            "deep_code_analyzer_high": "deep_code_analyzer_high",
            "deep_code_analyzer_medium": "deep_code_analyzer_medium",
            "deep_code_analyzer_low": "deep_code_analyzer_low",
        },
    )

    # Deep analysis → Handler
    graph.add_edge("deep_code_analyzer_high", "high_priority_handler")
    graph.add_edge("deep_code_analyzer_medium", "medium_priority_handler")
    graph.add_edge("deep_code_analyzer_low", "low_priority_handler")

    # After handlers, check remaining priorities
    graph.add_conditional_edges(
        "high_priority_handler",
        route_after_high,
        {
            "deep_code_analyzer_medium": "deep_code_analyzer_medium",
            "deep_code_analyzer_low": "deep_code_analyzer_low",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "medium_priority_handler",
        route_after_medium,
        {
            "deep_code_analyzer_low": "deep_code_analyzer_low",
            END: END,
        },
    )

    graph.add_edge("low_priority_handler", END)

    return graph


# Compiled graph (singleton)
pipeline = build_pipeline().compile()


async def run_pipeline(trigger_type: str = "manual") -> dict[str, Any]:
    """
    Execute the full agent pipeline.

    Data flows through PostgreSQL between agents:
    1. Agent 1 reads raw_logs → segregates → stores in cloud_logs
    2. Agent 2 reads cloud_logs from DB → analyzes with Gemini
    3. Agent 3+ classifies and handles based on priority
    
    Args:
        trigger_type: "manual" or "scheduler"
    
    Returns:
        Pipeline result summary
    """
    run_id = str(uuid.uuid4())
    logger.info(f"Pipeline run started: {run_id} (trigger: {trigger_type})")

    # Create AgentRun record
    agent_run = None
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

    # Broadcast pipeline start
    await _broadcast("pipeline_start", {"run_id": run_id, "trigger": trigger_type})

    # Initial state — data flows through PostgreSQL, not the state dict
    initial_state: PipelineState = {
        "run_id": run_id,
        "trigger_type": trigger_type,
        "started_at": datetime.utcnow().isoformat(),
        "current_agent": "starting",
        "status": "running",
        "segregated_log_ids": [],
        "total_logs_extracted": 0,
        "segregation_summary": {},
        "issues_found": [],
        "has_issues": False,
        "level_distribution": {},
        "category_distribution": {},
        "classified_issues": [],
        "high_priority_incidents": [],
        "medium_priority_incidents": [],
        "low_priority_incidents": [],
        "deep_analysis_high": [],
        "deep_analysis_medium": [],
        "deep_analysis_low": [],
        "high_priority_solutions": [],
        "medium_priority_solutions": [],
        "low_priority_solutions": [],
        "emails_sent": [],
        "medium_emails_sent": [],
        "low_emails_sent": [],
        "low_priority_logged": 0,
        "export_paths": [],
        "errors": [],
    }

    try:
        # Run the pipeline
        result = await pipeline.ainvoke(initial_state)

        # Update AgentRun record
        try:
            async with async_session() as session:
                # pyrefly: ignore [missing-import]
                from sqlalchemy import update
                await session.execute(
                    update(AgentRun)
                    .where(AgentRun.id == run_id)
                    .values(
                        status=AgentRunStatus.SUCCESS,
                        completed_at=datetime.utcnow(),
                        logs_processed=result.get("total_logs_extracted", 0),
                        incidents_created=len(result.get("classified_issues", [])),
                        high_priority_count=len(result.get("high_priority_incidents", [])),
                        medium_priority_count=len(result.get("medium_priority_incidents", [])),
                        low_priority_count=len(result.get("low_priority_incidents", [])),
                        emails_sent=len(result.get("emails_sent", [])),
                    )
                )
                await session.commit()
        except Exception as e:
            logger.warning(f"Failed to update AgentRun record: {e}")

        await _broadcast("pipeline_complete", {
            "run_id": run_id,
            "status": "completed",
            "logs_processed": result.get("total_logs_extracted", 0),
            "incidents": len(result.get("classified_issues", [])),
        })

        logger.info(f"Pipeline run completed: {run_id}")
        return {
            "run_id": run_id,
            "status": "completed",
            "logs_processed": result.get("total_logs_extracted", 0),
            "issues_found": len(result.get("issues_found", [])),
            "high_priority": len(result.get("high_priority_incidents", [])),
            "medium_priority": len(result.get("medium_priority_incidents", [])),
            "low_priority": len(result.get("low_priority_incidents", [])),
            "emails_sent": len(result.get("emails_sent", [])),
            "export_paths": result.get("export_paths", []),
        }

    except Exception as e:
        logger.error(f"Pipeline run failed: {run_id}: {e}")

        # Update AgentRun as failed
        try:
            async with async_session() as session:
                # pyrefly: ignore [missing-import]
                from sqlalchemy import update
                await session.execute(
                    update(AgentRun)
                    .where(AgentRun.id == run_id)
                    .values(
                        status=AgentRunStatus.FAILED,
                        completed_at=datetime.utcnow(),
                        error_message=str(e),
                    )
                )
                await session.commit()
        except Exception:
            pass

        await _broadcast("pipeline_error", {"run_id": run_id, "error": str(e)})

        return {
            "run_id": run_id,
            "status": "failed",
            "error": str(e),
        }
