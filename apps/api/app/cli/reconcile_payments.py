"""Reconciliation command — see docs/payments.md#10-reconciliation-command.

Run with: `python -m app.cli.reconcile_payments [--older-than-minutes N] [--dry-run]`

Cross-checks every `payments` row still `pending` against the provider's
own API (never the client) and settles it if the provider says otherwise —
the fallback path for a payment whose webhook delivery was lost, delayed,
or never sent. Intended to be invoked periodically (cron/task scheduler);
no such scheduler exists in this environment yet, so this is a standalone,
manually (or externally) triggered script rather than a background job.
"""

import argparse
import sys

from app.core.alerts import send_alert
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import observe_background_job
from app.db.session import get_sessionmaker
from app.services.payments.service import reconcile_pending_payments

logger = get_logger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reconcile pending booking payments.")
    parser.add_argument(
        "--older-than-minutes",
        type=int,
        default=15,
        help="Only reconcile payments that have been pending at least this long (default 15).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without committing.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    configure_logging(get_settings().log_level)
    session = get_sessionmaker()()
    try:
        changed = reconcile_pending_payments(session, older_than_minutes=args.older_than_minutes)
        if args.dry_run:
            session.rollback()
            logger.info("reconciliation_dry_run", changed=changed)
        else:
            session.commit()
            logger.info("reconciliation_complete", changed=changed)
        observe_background_job("reconcile_payments", success=True)
        return 0
    except Exception as exc:
        session.rollback()
        observe_background_job("reconcile_payments", success=False)
        send_alert("background_job_failed", job="reconcile_payments", error=str(exc))
        logger.error("reconciliation_failed", exc_info=True)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
