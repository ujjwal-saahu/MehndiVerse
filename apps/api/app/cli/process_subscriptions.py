"""Subscription expiration / grace-period command — see
docs/subscriptions-and-entitlements.md#grace-period.

Run with: `python -m app.cli.process_subscriptions [--dry-run]`

Transitions `active` subscriptions whose period has ended into either
`expired` (if cancelled) or `past_due` (grace period, entitlements still
active) with no successful renewal, and expires `past_due` subscriptions
whose grace period has elapsed — mirrors
`app/cli/reconcile_payments.py`'s "no scheduler exists in this environment
yet" standalone-script shape exactly.
"""

import argparse
import sys

from app.core.alerts import send_alert
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import observe_background_job
from app.db.session import get_sessionmaker
from app.services.subscriptions import process_due_subscriptions

logger = get_logger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Expire due subscriptions and apply/clear grace periods."
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
        changed = process_due_subscriptions(session)
        if args.dry_run:
            session.rollback()
            logger.info("process_subscriptions_dry_run", changed=changed)
        else:
            session.commit()
            logger.info("process_subscriptions_complete", changed=changed)
        observe_background_job("process_subscriptions", success=True)
        return 0
    except Exception as exc:
        session.rollback()
        observe_background_job("process_subscriptions", success=False)
        send_alert("background_job_failed", job="process_subscriptions", error=str(exc))
        logger.error("process_subscriptions_failed", exc_info=True)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
