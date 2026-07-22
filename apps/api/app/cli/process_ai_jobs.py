"""AI background-job worker — see docs/ai-foundation.md#background-job-
processing.

Run with: `python -m app.cli.process_ai_jobs [--limit N] [--stuck-after-seconds N] [--dry-run]`

Mirrors `app/cli/reconcile_payments.py`/`app/cli/process_subscriptions.py`'s
exact "no scheduler exists in this environment yet, so this is a
standalone, manually/externally-triggered script" shape — intended to be
invoked periodically (cron/task scheduler) or run continuously by an
operator wrapping it in a loop; running more than one instance
simultaneously is safe (see `app/services/ai/jobs.py::claim_due_jobs`'s
`SELECT ... FOR UPDATE SKIP LOCKED` claim).

`--dry-run` only covers `requeue_stuck_jobs` (a pure bookkeeping pass with
no provider calls, so rolling it back is meaningful). It does not cover
`process_due_jobs`: each job it claims is committed the moment it finishes
(success or failure) as part of the queue's own crash-safety design — see
`jobs.py`'s module docstring — so there's no batch of pending changes a
"dry run" could meaningfully preview or discard. Passing `--dry-run` skips
calling `process_due_jobs` entirely rather than half-honoring the flag.
"""

import argparse
import sys

from app.core.alerts import send_alert
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import AI_JOB_QUEUE_DEPTH, observe_background_job
from app.db.session import get_sessionmaker
from app.services.ai.jobs import count_pending_ai_jobs, process_due_jobs, requeue_stuck_jobs

logger = get_logger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process due AI background jobs.")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of jobs to claim and process in this run (default 20).",
    )
    parser.add_argument(
        "--stuck-after-seconds",
        type=int,
        default=None,
        help="Override ai_job_stuck_after_seconds for the requeue pass.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only run (and roll back) the stuck-job requeue pass; skip processing due jobs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    configure_logging(get_settings().log_level)
    session = get_sessionmaker()()
    try:
        requeued = requeue_stuck_jobs(session, stuck_after_seconds=args.stuck_after_seconds)
        if args.dry_run:
            session.rollback()
            logger.info("process_ai_jobs_dry_run", requeued=requeued)
            return 0
        session.commit()

        summary = process_due_jobs(session, limit=args.limit)
        pending_depth = count_pending_ai_jobs(session)
        AI_JOB_QUEUE_DEPTH.observe(pending_depth)
        logger.info(
            "process_ai_jobs_complete",
            requeued=requeued,
            claimed=summary.claimed,
            completed=summary.completed,
            failed=summary.failed,
            pending_depth=pending_depth,
        )
        observe_background_job("process_ai_jobs", success=True)
        return 0
    except Exception as exc:
        session.rollback()
        observe_background_job("process_ai_jobs", success=False)
        send_alert("background_job_failed", job="process_ai_jobs", error=str(exc))
        logger.error("process_ai_jobs_failed", exc_info=True)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
