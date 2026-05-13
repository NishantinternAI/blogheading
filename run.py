# run.py
import subprocess
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from mergeall_engine import run_pipeline
from storage.save_output import save_output
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

DEFAULT_COUNTRY  = "India"
DEFAULT_CATEGORY = "finance"

def run_job():
    log.info("Pipeline job started")
    try:
        output  = run_pipeline(DEFAULT_COUNTRY, DEFAULT_CATEGORY)
        results = output.get("results", []) if isinstance(output, dict) else output

        if not results:
            log.warning("No results returned")
            return

        log.info(f"Pipeline job completed — {len(results)} blogs saved")

    except Exception as e:
        log.error(f"Pipeline job failed: {e}", exc_info=True)

if __name__ == "__main__":
    # ── Start scheduler in background ────────────────────────
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func             = run_job,
        trigger          = CronTrigger(minute="*/5"),
        id               = "blog_pipeline_job",
        name             = "Blog Pipeline — every 5 min",
        replace_existing = True,
        max_instances    = 1
    )

    # run once immediately on startup
    log.info("Running pipeline once on startup...")
    run_job()

    scheduler.start()
    log.info("Scheduler started — pipeline runs every 5 minutes")

    # ── Start Streamlit in main process ──────────────────────
    try:
        subprocess.run(["streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.shutdown()
        log.info("Scheduler stopped")