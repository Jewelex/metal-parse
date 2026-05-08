# test_scheduler.py
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import time
import logging

# Indian Standard Time
IST = timezone(timedelta(hours=5, minutes=30))

sys.path.insert(0, str(Path(__file__).parent))
from scrape_metals import main as run_scraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_scraper_with_logging():
    try:
        logging.info("=" * 50)
        logging.info("🚀 Test scraper run triggered!")
        logging.info(f"Time (IST): {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}")

        run_scraper()

        logging.info("✅ Scraper completed successfully!")
        logging.info("=" * 50)

    except Exception as e:
        logging.error(f"❌ Scraper failed: {e}")
        logging.exception("Full traceback:")

def main():
    now_ist = datetime.now(IST)

    # Schedule 1 min and 2 min from now
    run_1 = now_ist + timedelta(minutes=1)
    run_2 = now_ist + timedelta(minutes=2)

    scheduler = BackgroundScheduler(timezone=IST)

    scheduler.add_job(
        func=run_scraper_with_logging,
        trigger=DateTrigger(run_date=run_1, timezone=IST),
        id='test_run_1',
        name=f'Test Run 1 - {run_1.strftime("%H:%M:%S")} IST'
    )

    scheduler.add_job(
        func=run_scraper_with_logging,
        trigger=DateTrigger(run_date=run_2, timezone=IST),
        id='test_run_2',
        name=f'Test Run 2 - {run_2.strftime("%H:%M:%S")} IST'
    )

    scheduler.start()

    logging.info("=" * 50)
    logging.info("🧪 TEST SCHEDULER STARTED")
    logging.info(f"Current Time (IST): {now_ist.strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("")
    logging.info("Scheduled test runs:")
    logging.info(f"  ⏰ Run 1 → {run_1.strftime('%H:%M:%S')} IST  (1 min from now)")
    logging.info(f"  ⏰ Run 2 → {run_2.strftime('%H:%M:%S')} IST  (2 min from now)")
    logging.info("")
    logging.info("Wait and watch... will auto-exit after both runs.")
    logging.info("=" * 50)

    try:
        # Wait max 4 minutes, then auto-exit
        for i in range(240):
            time.sleep(1)
            remaining = len(scheduler.get_jobs())
            if remaining == 0:
                logging.info("✅ All test runs completed! Exiting.")
                break
        else:
            logging.info("⏱️ Timeout reached. Exiting.")
    except KeyboardInterrupt:
        logging.info("Stopped by user.")
    finally:
        scheduler.shutdown()

if __name__ == "__main__":
    main()
