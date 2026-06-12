# pyright: ignore[reportMissingImports]
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from database import SessionLocal
from services.job_fetch_service import process_and_normalize_jobs

logger = logging.getLogger(__name__)

def run_job_aggregation():
    """Trigger job aggregation task."""
    logger.info("Scheduler: Triggering job aggregation task...")
    db = SessionLocal()
    try:
        summary = process_and_normalize_jobs(db)
        logger.info(f"Scheduler: Job aggregation complete. {summary}")
    except Exception as e:
        logger.error(f"Scheduler: Error during job aggregation: {e}", exc_info=True)
    finally:
        db.close()

scheduler = BackgroundScheduler()

def start_scheduler():
    """Start the background scheduler."""
    if not scheduler.running:
        # Run every 6 hours
        scheduler.add_job(run_job_aggregation, "interval", hours=6, id="job_aggregation_task", replace_existing=True)
        # Also run once on startup asynchronously to populate jobs immediately
        scheduler.add_job(run_job_aggregation, id="startup_job_aggregation", replace_existing=True)
        scheduler.start()
        logger.info("Scheduler: Background scheduler started. Job aggregation will run every 6 hours.")

def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler: Background scheduler stopped.")
