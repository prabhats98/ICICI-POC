"""
Pipeline State — Shared state definition for the 8-agent LangGraph pipeline.

Flow: Log Collector → Preprocessing → Classification → Priority
      → Context → Resolution → Orchestrator → Notification
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

    # --- Time range filter (GMT) ---
    time_range_start: str  # ISO 8601 GMT start datetime (optional)
    time_range_end: str  # ISO 8601 GMT end datetime (optional)
    no_logs_found: bool  # True when time-range query returned zero logs

    # --- Log Collector outputs ---
    total_collected: int
    per_source: dict[str, int]  # {"azure-front-door": 50, ...}
    raw_log_ids: list[str]

    # --- Preprocessing Engine outputs ---
    total_preprocessed: int
    level_counts: dict[str, int]
    category_counts: dict[str, int]
    cloud_log_ids: list[str]
    duplicates_removed: int

    # --- Classification Agent outputs ---
    issues_found: list[dict[str, Any]]
    has_issues: bool
    logs_analyzed: int

    # --- Priority Agent outputs ---
    classified_issues: list[dict[str, Any]]
    p1_incidents: list[dict[str, Any]]
    p2_incidents: list[dict[str, Any]]
    p3_incidents: list[dict[str, Any]]

    # --- Context Agent outputs ---
    context_enriched_incidents: list[dict[str, Any]]

    # --- Resolution Agent outputs ---
    resolutions: list[dict[str, Any]]

    # --- Orchestrator Agent outputs ---
    summary: dict[str, Any]
    notifications_to_send: list[dict[str, Any]]

    # --- Notification Agent outputs ---
    emails_sent: list[str]
    email_failures: list[str]

    # --- Export ---
    export_paths: list[str]

    # --- Errors ---
    errors: list[str]
