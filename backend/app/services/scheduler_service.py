"""
Scheduler Service - APScheduler configuration for periodic log extraction.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def run_pipeline_job():
    """Scheduled job that triggers the agent pipeline."""
    from app.agents.graph import run_pipeline

    logger.info("Scheduler triggered: Starting agent pipeline run...")
    try:
        result = await run_pipeline(trigger_type="scheduler")
        logger.info(f"Scheduled pipeline run completed: {result.get('status', 'unknown')}")
    except Exception as e:
        logger.error(f"Scheduled pipeline run failed: {e}")


def start_scheduler():
    """Start the APScheduler with configured interval."""
    scheduler.add_job(
        run_pipeline_job,
        trigger=IntervalTrigger(minutes=settings.scheduler_interval_minutes),
        id="log_extraction_pipeline",
        name="Log Extraction & Analysis Pipeline",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )
    scheduler.start()
    logger.info(
        f"Scheduler started: pipeline runs every {settings.scheduler_interval_minutes} minutes"
    )


def stop_scheduler():
    """Stop the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_next_run_time():
    """Get the next scheduled run time."""
    job = scheduler.get_job("log_extraction_pipeline")
    if job:
        return job.next_run_time
    return None
