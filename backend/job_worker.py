"""
Dedicated background worker for the two-hour job synchronization.

Usage (from the backend directory):
    python job_worker.py            # run forever, sync whenever due
    python job_worker.py --once     # run one sync now if due, then exit

Run exactly like the web app (same .env / DATABASE_URL). Several workers may
run at once; the database lease guarantees only one sync executes at a time.
"""
import argparse
import logging
import signal
import threading

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main():
    parser = argparse.ArgumentParser(description="SkillBridge job sync worker")
    parser.add_argument("--once", action="store_true", help="run a sync if due, then exit")
    args = parser.parse_args()

    from app import app
    from utils.job_discovery.scheduler import run_forever, run_if_due

    if args.once:
        result = run_if_due(app)
        print(result if result else "Not due yet - nothing to do.")
        return

    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, lambda *_: stop.set())
        except (ValueError, OSError):
            pass
    run_forever(app, stop)


if __name__ == "__main__":
    main()
