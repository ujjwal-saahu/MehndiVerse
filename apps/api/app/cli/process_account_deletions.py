"""Account-deletion finalization command — see
docs/security-review.md#account-deletion.

Run with: `python -m app.cli.process_account_deletions [--dry-run]`

Anonymizes any account whose deletion grace period
(`account_deletion_grace_period_days`) has elapsed since
`POST /auth/account/deletion-request` was called — mirrors
app/cli/process_subscriptions.py's exact standalone-script shape.
"""

import argparse
import sys

from app.core.alerts import send_alert
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import observe_background_job
from app.db.session import get_sessionmaker
from app.services.account_deletion import process_pending_deletions

logger = get_logger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Anonymize accounts whose deletion grace period has elapsed."
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
        results = process_pending_deletions(session)
        if args.dry_run:
            session.rollback()
            logger.info("process_account_deletions_dry_run", count=len(results))
        else:
            session.commit()
            logger.info("process_account_deletions_complete", count=len(results))
        observe_background_job("process_account_deletions", success=True)
        return 0
    except Exception as exc:
        session.rollback()
        observe_background_job("process_account_deletions", success=False)
        send_alert("background_job_failed", job="process_account_deletions", error=str(exc))
        logger.error("process_account_deletions_failed", exc_info=True)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
