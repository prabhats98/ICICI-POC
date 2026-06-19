"""
Scheduler Service — APScheduler for periodic pipeline execution.
6-hour interval, overlap protection, retry with backoff.
"""

import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global scheduler instance
scheduler = AsyncIOScheduler()

# Pipeline enabled state (can be toggled via API)
_pipeline_enabled: bool = settings.pipeline_enabled


def is_pipeline_enabled() -> bool:
    """Check if the pipeline is currently enabled."""
    return _pipeline_enabled


def set_pipeline_enabled(enabled: bool) -> None:
    """Toggle the pipeline on or off."""
    global _pipeline_enabled
    _pipeline_enabled = enabled
    logger.info(f"Pipeline {'enabled' if enabled else 'disabled'}")


async def run_pipeline_job():
    """Scheduled job that triggers the agent pipeline with retry."""
    if not _pipeline_enabled:
        logger.info("Scheduler: Pipeline is disabled, skipping run")
        return

    from app.agents.graph import run_pipeline

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Scheduler: Starting pipeline run (attempt {attempt}/{max_retries})...")
            result = await run_pipeline(trigger_type="scheduler")
            status = result.get("status", "unknown")
            logger.info(f"Scheduler: Pipeline run completed with status: {status}")
            return
        except Exception as e:
            logger.error(f"Scheduler: Pipeline attempt {attempt} failed: {e}")
            if attempt < max_retries:
                backoff = 2 ** attempt * 10  # 20s, 40s, 80s
                logger.info(f"Scheduler: Retrying in {backoff}s...")
                await asyncio.sleep(backoff)
            else:
                logger.error("Scheduler: All retry attempts exhausted")


def start_scheduler():
    """Start the scheduler if enabled in config."""
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled in configuration")
        return

    scheduler.add_job(
        run_pipeline_job,
        trigger=IntervalTrigger(hours=settings.scheduler_interval_hours),
        id="pipeline_scheduler",
        name=f"Pipeline Scheduler (every {settings.scheduler_interval_hours}h)",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )
    scheduler.start()
    logger.info(
        f"Scheduler started: pipeline runs every {settings.scheduler_interval_hours} hours"
    )


def stop_scheduler():
    """Stop the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def pause_scheduler():
    """Pause the scheduled job."""
    job = scheduler.get_job("pipeline_scheduler")
    if job:
        job.pause()
        logger.info("Scheduler paused")


def resume_scheduler():
    """Resume the scheduled job."""
    job = scheduler.get_job("pipeline_scheduler")
    if job:
        job.resume()
        logger.info("Scheduler resumed")


def get_next_run_time():
    """Get the next scheduled run time."""
    job = scheduler.get_job("pipeline_scheduler")
    if job:
        return job.next_run_time
    return None


def get_scheduler_status() -> dict:
    """Full scheduler status for the API."""
    job = scheduler.get_job("pipeline_scheduler")
    return {
        "enabled": settings.scheduler_enabled,
        "pipeline_enabled": _pipeline_enabled,
        "scheduler_running": scheduler.running,
        "interval_hours": settings.scheduler_interval_hours,
        "next_run_at": str(job.next_run_time) if job and job.next_run_time else None,
        "job_state": str(job.next_run_time is not None) if job else "no_job",
    }
