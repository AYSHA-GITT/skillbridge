"""
Two-hour job synchronization scheduler.

The schedule is stored in the database (JobSyncRun history), not in process
memory, so it survives restarts, deploys and sleeping hosts:

    due  <=>  now >= last_attempt.started_at + 2h        (after success/partial)
              now >= last_attempt.started_at + 20min     (after a failed run)

Overlap is impossible because every run first acquires the `job_sync`
database lease (see sync_service.acquire_lease).

Three ways to drive it in production (pick one; combining them is safe):

1. Dedicated worker process (recommended for always-on hosts / Docker / VMs):
       python job_worker.py
   Polls every JOB_SCHEDULER_POLL_SECONDS (default 60) and runs a sync when due.

2. Platform cron (Render/Railway cron jobs, GitHub Actions, systemd timer, crontab):
       */15 * * * *  cd backend && flask --app app jobs sync-if-due
   Each invocation exits immediately unless a sync is due, so a frequent
   cron schedule still yields one sync every two hours.

3. In-process thread (single-instance development only):
       RUN_JOB_SCHEDULER_IN_PROCESS=1
   Convenient locally; not recommended for production web workers that can
   be put to sleep or scaled to zero.
"""
import logging
import os
import socket
import threading
from typing import Optional

logger = logging.getLogger("skillbridge.job_scheduler")

POLL_SECONDS = float(os.getenv("JOB_SCHEDULER_POLL_SECONDS", "60"))


def run_if_due(app, trigger: str = "scheduled") -> Optional[dict]:
    from utils.job_discovery.sync_service import is_due, run_job_sync
    with app.app_context():
        if not is_due():
            return None
        return run_job_sync(trigger=trigger)


def heartbeat(app, owner: str) -> None:
    """Record that this scheduler is alive (visible in the admin dashboard / CLI)."""
    from utils.job_discovery.sync_service import record_scheduler_heartbeat
    with app.app_context():
        record_scheduler_heartbeat(owner)


def worker_owner(kind: str = "worker") -> str:
    return f"{kind}:{socket.gethostname()}:{os.getpid()}"


def run_forever(app, stop_event: Optional[threading.Event] = None, owner: Optional[str] = None,
                max_iterations: Optional[int] = None) -> None:
    logger.info("Job scheduler started (poll every %ss)", POLL_SECONDS)
    stop_event = stop_event or threading.Event()
    owner = owner or worker_owner()
    iterations = 0
    while not stop_event.is_set():
        iterations += 1
        try:
            heartbeat(app, owner)
            result = run_if_due(app)
            if result:
                logger.info("Scheduled job sync finished with status=%s", result.get("status"))
        except Exception:
            # never let one bad iteration kill the scheduler
            logger.exception("Scheduler iteration failed")
            try:
                with app.app_context():
                    from extensions import db
                    db.session.rollback()
            except Exception:
                pass
        if max_iterations is not None and iterations >= max_iterations:
            break
        stop_event.wait(POLL_SECONDS)


_thread: Optional[threading.Thread] = None


def start_in_process_scheduler(app) -> bool:
    """Start a daemon thread (dev convenience). Returns True if started."""
    global _thread
    if _thread is not None and _thread.is_alive():
        return False
    # Flask's debug reloader imports the app twice; only run in the serving child
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return False
    _thread = threading.Thread(target=run_forever, args=(app,), kwargs={"owner": worker_owner("in-process")},
                               name="job-scheduler", daemon=True)
    _thread.start()
    return True
