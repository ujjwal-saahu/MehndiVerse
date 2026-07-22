"""app/cli/reconcile_payments.py — see docs/payments.md#10-reconciliation-
command. Only argument parsing is exercised here: `main()` opens a session
against the configured database directly (not the isolated per-test
transaction other tests use), so the actual reconciliation logic is tested
through `reconcile_pending_payments()` in test_reconciliation.py instead."""

from app.cli.reconcile_payments import build_arg_parser


def test_default_arguments() -> None:
    args = build_arg_parser().parse_args([])
    assert args.older_than_minutes == 15
    assert args.dry_run is False


def test_accepts_older_than_minutes_and_dry_run_flags() -> None:
    args = build_arg_parser().parse_args(["--older-than-minutes", "30", "--dry-run"])
    assert args.older_than_minutes == 30
    assert args.dry_run is True
