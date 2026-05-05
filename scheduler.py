# scheduler.py
import sys
import os
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import time
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import your scraper function
from scrape_metals import main as run_scraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_scraper_with_logging():
    """Wrapper function to run scraper with logging"""
    try:
        logging.info("="*50)
        logging.info("🚀 Starting scheduled scraper run...")
        logging.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run the main scraper
        run_scraper()
        
        logging.info("✅ Scraper completed successfully!")
        logging.info("="*50)
        
    except Exception as e:
        logging.error(f"❌ Scraper failed: {e}")
        logging.exception("Full traceback:")

def main():
    """Setup and run scheduler"""
    
    # Create scheduler
    scheduler = BackgroundScheduler()
    
    # Schedule jobs at specific times
    # Format: CronTrigger(hour=9, minute=58)
    
    # 9:58 AM
    scheduler.add_job(
        func=run_scraper_with_logging,
        trigger=CronTrigger(hour=9, minute=58),
        id='morning_run',
        name='Morning Run - 9:58 AM',
        replace_existing=True
    )
    
    # 12:58 PM
    scheduler.add_job(
        func=run_scraper_with_logging,
        trigger=CronTrigger(hour=12, minute=58),
        id='afternoon_run',
        name='Afternoon Run - 12:58 PM',
        replace_existing=True
    )
    
    # 3:58 PM
    scheduler.add_job(
        func=run_scraper_with_logging,
        trigger=CronTrigger(hour=15, minute=58),
        id='evening_run',
        name='Evening Run - 3:58 PM',
        replace_existing=True
    )
    
    # Start scheduler
    scheduler.start()
    
    logging.info("="*50)
    logging.info(" Metal Rate Bot Scheduler Started")
    logging.info(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("Scheduled runs:")
    
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        logging.info(f"  - {job.name}: {next_run.strftime('%H:%M:%S') if next_run else 'Not scheduled'}")
    
    logging.info("="*50)
    logging.info("Press Ctrl+C to stop scheduler")
    
    try:
        # Keep scheduler running
        while True:
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logging.info("Scheduler stopped by user")
        scheduler.shutdown()

if __name__ == "__main__":
    main()