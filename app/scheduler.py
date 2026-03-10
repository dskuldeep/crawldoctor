"""Scheduler service for periodic tasks."""
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import structlog

from app.database import SessionLocal
from app.config import settings
from app.services.backfill import BackfillService

logger = structlog.get_logger()

class SchedulerService:
    """Manages background scheduled tasks."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.backfill_service = BackfillService()
        
    def start(self):
        """Start the scheduler and add jobs."""
        if not self.scheduler.running:
            # Add backfill job on a configurable interval
            self.scheduler.add_job(
                self._run_backfill,
                trigger=IntervalTrigger(minutes=settings.summary_backfill_interval_minutes),
                id='periodic_backfill',
                name='Periodic Data Backfill',
                replace_existing=True
            )
            self.scheduler.start()
            logger.info(
                "Scheduler started with periodic backfill job",
                interval_minutes=settings.summary_backfill_interval_minutes
            )

    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shut down")

    def _run_backfill(self):
        """Execute the backfill process."""
        try:
            logger.info("Starting scheduled backfill job")
            db = SessionLocal()
            try:
                # Run backfill for configured lookback window
                result = self.backfill_service.backfill_all(db, days=settings.summary_backfill_days)
                logger.info("Scheduled backfill completed", result=result)
            finally:
                db.close()
        except Exception as e:
            logger.error("Scheduled backfill failed", error=str(e))
