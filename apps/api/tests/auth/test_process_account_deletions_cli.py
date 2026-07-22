"""app/cli/process_account_deletions.py — see
docs/security-review.md#account-deletion. Only argument parsing is
exercised here, mirroring tests/subscriptions/test_process_subscriptions_
cli.py: the actual anonymization logic is tested through
process_pending_deletions() in test_account_deletion_finalization.py."""

from app.cli.process_account_deletions import build_arg_parser


def test_default_arguments() -> None:
    args = build_arg_parser().parse_args([])
    assert args.dry_run is False


def test_accepts_dry_run_flag() -> None:
    args = build_arg_parser().parse_args(["--dry-run"])
    assert args.dry_run is True
