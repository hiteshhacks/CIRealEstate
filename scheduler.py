"""
Scheduler — runs the scraper automatically at a fixed interval.

Usage:
    python scheduler.py

This starts an APScheduler background process that triggers the scrape
pipeline every SCRAPE_INTERVAL_HOURS (default: 6 hours).
It also runs one scrape immediately on startup.
"""

import os
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from scraper import run_scrape_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCRAPE_INTERVAL_HOURS = int(os.environ.get("SCRAPE_INTERVAL_HOURS", "6"))
TARGET_COUNT = int(os.environ.get("SCRAPE_TARGET_COUNT", "300"))


def job():
    logger.info("=== Scheduled scrape starting ===")
    result = run_scrape_pipeline(target_count=TARGET_COUNT)
    logger.info("=== Scheduled scrape finished: %s ===", result)


if __name__ == "__main__":
    logger.info(
        "Scheduler started. Scraping every %d hours (target: %d listings).",
        SCRAPE_INTERVAL_HOURS,
        TARGET_COUNT,
    )

    # Run once immediately on startup
    job()

    scheduler = BlockingScheduler()
    scheduler.add_job(job, "interval", hours=SCRAPE_INTERVAL_HOURS)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
