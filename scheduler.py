from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from mergeall_engine import run_pipeline
import logging

# ── Logging setup ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────
DEFAULT_COUNTRY  = "India"
DEFAULT_CATEGORY = "finance"

# ── Job function ──────────────────────────────────────────────
def run_job():
    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log.info("  🚀 Pipeline job started")
    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    try:
        output  = run_pipeline(DEFAULT_COUNTRY, DEFAULT_CATEGORY)
        results = output.get("results", []) if isinstance(output, dict) else output

        if not results:
            log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            log.info("  📰 No new content available yet")
            log.info("  ⏳ Waiting for RSS to refresh")
            log.info("  ⏭  Will retry in next scheduled run")
            log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            return

        log.info(f"  ✅ Pipeline completed — {len(results)} blogs processed")

    except Exception as e:
        log.error(f"  ❌ Pipeline job failed: {e}", exc_info=True)

# ── Scheduler setup ───────────────────────────────────────────
if __name__ == "__main__":
    scheduler = BlockingScheduler()

    scheduler.add_job(
        func               = run_job,
        trigger            = CronTrigger(minute="*/15"),  # ← every 30 min
        id                 = "blog_pipeline_job",
        name               = "Blog Pipeline — every 15 min",
        replace_existing   = True,
        max_instances      = 1,        # ← only 1 run at a time
        # misfire_grace_time = 60
    )

    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log.info("  🚀 Scheduler started")
    log.info("  ⏱  Pipeline runs every 15 minutes")
    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    run_job()  # ← run immediately on start

    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("Scheduler stopped")
        scheduler.shutdown()


# from apscheduler.schedulers.blocking import BlockingScheduler
# from apscheduler.triggers.cron import CronTrigger
# from mergeall_engine import run_pipeline
# from AI_GEN.get_system_timestamp import get_run_timestamp
# import logging
#       # must bind to 0.0.0.0, not localhost

# # ── Logging setup ─────────────────────────────────────────────
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
#     handlers=[
#         logging.FileHandler("scheduler.log"),
#         logging.StreamHandler()
#     ]
# )
# log = logging.getLogger(__name__)

# # ── Constants ─────────────────────────────────────────────────
# DEFAULT_COUNTRY  = "India"
# DEFAULT_CATEGORY = "finance"

# # ── Job function ──────────────────────────────────────────────
# def run_job():
#     log.info("Pipeline job started")
#     try:
#         output   = run_pipeline(DEFAULT_COUNTRY, DEFAULT_CATEGORY)
#         results  = output.get("results", []) if isinstance(output, dict) else output

#         if not results:
#             log.warning("No results returned from pipeline")
#             return

        

#         log.info(f"Pipeline job completed — {len(results)} blogs processed")

#     except Exception as e:
#         log.error(f"Pipeline job failed: {e}", exc_info=True)

# # ── Scheduler setup ───────────────────────────────────────────
# if __name__ == "__main__":
#     scheduler = BlockingScheduler()

#     scheduler.add_job(
#         func    = run_job,
#         trigger = CronTrigger(minute="*/5"),   # every 10 minutes
#         id      = "blog_pipeline_job",
#         name    = "Blog Pipeline — every 5 min",
#         replace_existing = True
#     )

#     log.info("Scheduler started — pipeline runs every 5 minutes")
#     log.info("Press Ctrl+C to stop")
#     run_job()  # ← runs immediately on start

#     try:
#         scheduler.start()
#     except KeyboardInterrupt:
#         log.info("Scheduler stopped")
#         scheduler.shutdown()