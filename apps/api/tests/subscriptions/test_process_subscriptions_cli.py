"""app/cli/process_subscriptions.py — see
docs/subscriptions-and-entitlements.md#grace-period. Only argument parsing
is exercised here, mirroring tests/payments/test_reconciliation_cli.py: the
actual expiration logic is tested through `process_due_subscriptions()` in
test_cancellation_and_expiration.py instead."""

from app.cli.process_subscriptions import build_arg_parser


def test_default_arguments() -> None:
    args = build_arg_parser().parse_args([])
    assert args.dry_run is False


def test_accepts_dry_run_flag() -> None:
    args = build_arg_parser().parse_args(["--dry-run"])
    assert args.dry_run is True
