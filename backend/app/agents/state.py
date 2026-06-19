"""
Pipeline State - Shared state definition for the LangGraph agent pipeline.
This TypedDict is passed between all agent nodes in the workflow.

Data Flow:
  raw_logs (DB) → Agent 1 [segregate] → cloud_logs (DB) → Agent 2 [analyze] → Agent 3+ [classify/act]
"""

from typing import TypedDict, Any


class PipelineState(TypedDict, total=False):
    """Shared state flowing through the LangGraph pipeline."""

    # --- Pipeline metadata ---
    run_id: str
    trigger_type: str  # "scheduler" or "manual"
    started_at: str
    current_agent: str
    status: str  # "running", "completed", "failed"

    # --- Agent 1: Log Extractor & Segregator outputs ---
    segregated_log_ids: list[str]  # IDs of newly segregated CloudLog entries in PostgreSQL
    total_logs_extracted: int
    segregation_summary: dict[str, Any]  # {total, critical, error, warning, info, categories}

    # --- Agent 2: Anomaly Detector outputs ---
    analysis_result: dict[str, Any]  # Full Gemini analysis response
    issues_found: list[dict[str, Any]]
    has_issues: bool
    level_distribution: dict[str, int]  # Level breakdown of analyzed logs
    category_distribution: dict[str, int]  # Category breakdown of analyzed logs

    # --- Agent 3: Priority Classifier outputs ---
    classified_issues: list[dict[str, Any]]
    high_priority_incidents: list[dict[str, Any]]
    medium_priority_incidents: list[dict[str, Any]]
    low_priority_incidents: list[dict[str, Any]]

    # --- Agent 4a: High Priority Handler outputs ---
    high_priority_solutions: list[dict[str, Any]]
    emails_sent: list[str]

    # --- Agent 4b: Medium Priority Handler outputs ---
    medium_priority_solutions: list[dict[str, Any]]

    # --- Agent 4c: Low Priority Handler outputs ---
    low_priority_logged: int

    # --- Export ---
    export_paths: list[str]

    # --- Errors ---
    errors: list[str]
