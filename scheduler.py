"""
scheduler.py -- Live production entry point (docker-compose's `command: python3 scheduler.py`).

Runs run_pipeline() every 8 minutes via APScheduler's BlockingScheduler,
then hands the single newly-generated article to mcp_agent.run_agent(),
which drives Webflow publishing (webflow_poster.py) through tool-calling.

run.py is a second, unused scheduler (5-minute interval, launches
Streamlit as a subprocess) -- not referenced by docker-compose.yml or
the Dockerfile CMD. Treat it as legacy/alternative.
"""

import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from core.pipeline import run_pipeline
from publishing.mcp_agent import run_agent

logging.basicConfig(level=logging.INFO)

executors = {
    'default': ThreadPoolExecutor(1)
}

scheduler = BlockingScheduler(executors=executors)

@scheduler.scheduled_job('cron', minute='*/8')
def pipeline_job():
    """Runs one pipeline cycle, then hands the new article (if any) to the Webflow-publishing agent."""
    print("\n" + "━"*33)
    print("  Pipeline job started")
    print("━"*33)
    results = run_pipeline()
    print(f"  Pipeline completed — {len(results)} blogs processed")

    if results:
        # Hand control to the AI agent with the single generated entry
        run_agent(entry=results[0])


if __name__ == "__main__":
    print("━"*33)
    print("  🚀 Scheduler started")
    print("  ⏱  Pipeline runs every 8 minutes")
    print("━"*33)

    # Run once immediately on start, then let the cron job take over
    print("  ⚡ Running pipeline immediately on start...")
    pipeline_job()

    scheduler.start()
