# scheduler.py
import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import time
import logging

# Indian Standard Time
IST = timezone(timedelta(hours=5, minutes=30))

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import your scraper function
from scrape_metals import main as run_scraper

# ── Fix Windows emoji crash in logging ──────────────────────────
class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that replaces unencodable chars instead of crashing"""
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            msg = self.format(record).encode('ascii', errors='replace').decode('ascii')
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log', encoding='utf-8'),
        SafeStreamHandler()
    ]
)

def run_scraper_with_logging():
    """Wrapper function to run scraper with logging"""
    try:
        logging.info("=" * 50)
        logging.info("[START] Starting scheduled scraper run...")
        logging.info(f"Time (IST): {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}")
        
        run_scraper()
        
        logging.info("[DONE] Scraper completed successfully!")
        logging.info("=" * 50)
        
    except Exception as e:
        logging.error(f"[FAIL] Scraper failed: {e}")
        logging.exception("Full traceback:")

def main():
    """Setup and run scheduler"""
    
    # max_instances=1 → If a run is still going, the next trigger waits
    scheduler = BackgroundScheduler(timezone=IST)
    
    # 9:58 AM IST
    scheduler.add_job(
        func=run_scraper_with_logging,
        trigger=CronTrigger(hour=9, minute=58, timezone=IST),
        id='morning_run',
        name='Morning Run - 9:58 AM IST',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=300
    )
    
    # 12:58 PM IST
    scheduler.add_job(
        func=run_scraper_with_logging,
        trigger=CronTrigger(hour=12, minute=58, timezone=IST),
        id='afternoon_run',
        name='Afternoon Run - 12:58 PM IST',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=300
    )
    
    # 3:58 PM IST
    scheduler.add_job(
        func=run_scraper_with_logging,
        trigger=CronTrigger(hour=15, minute=58, timezone=IST),
        id='evening_run',
        name='Evening Run - 3:58 PM IST',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=300
    )
    
    scheduler.start()
    
    logging.info("=" * 50)
    logging.info("Metal Rate Bot Scheduler Started")
    logging.info(f"Current Time (IST): {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("Scheduled runs:")
    
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        if next_run:
            next_run_ist = next_run.astimezone(IST)
            logging.info(f"  - {job.name}: Next at {next_run_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")
        else:
            logging.info(f"  - {job.name}: Not scheduled")
    
    logging.info("=" * 50)
    logging.info("Press Ctrl+C to stop scheduler")
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Scheduler stopped by user")
        scheduler.shutdown()

if __name__ == "__main__":
    main()
