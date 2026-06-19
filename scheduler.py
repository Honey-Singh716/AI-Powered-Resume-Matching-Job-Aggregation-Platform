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

def run_job_aggregation_if_empty():
    """Trigger job aggregation task only if the database has no jobs."""
    logger.info("Scheduler: Checking if startup job aggregation is needed...")
    db = SessionLocal()
    try:
        from models.job import Job
        job_count = db.query(Job).count()
        if job_count == 0:
            logger.info("Scheduler: Database has 0 jobs. Triggering startup job aggregation...")
            summary = process_and_normalize_jobs(db)
            logger.info(f"Scheduler: Startup job aggregation complete. {summary}")
        else:
            logger.info(f"Scheduler: Database already contains {job_count} jobs. Skipping startup job aggregation.")
    except Exception as e:
        logger.error(f"Scheduler: Error during startup job aggregation: {e}", exc_info=True)
    finally:
        db.close()

scheduler = BackgroundScheduler()

def start_scheduler():
    """Start the background scheduler."""
    if not scheduler.running:
        # Run every 6 hours
        scheduler.add_job(run_job_aggregation, "interval", hours=6, id="job_aggregation_task", replace_existing=True)
        
        # Run once after a 2-minute delay to populate jobs if database is empty.
        # This allows the app to pass initial health checks and bind to the port immediately on boot.
        from datetime import datetime, timedelta
        run_time = datetime.now() + timedelta(minutes=2)
        scheduler.add_job(run_job_aggregation_if_empty, "date", run_date=run_time, id="startup_job_aggregation", replace_existing=True)
        
        scheduler.start()
        logger.info("Scheduler: Background scheduler started. Job aggregation will run every 6 hours.")

def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler: Background scheduler stopped.")
