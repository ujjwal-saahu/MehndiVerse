"""app/cli/process_ai_jobs.py — see docs/ai-foundation.md#background-job-
processing. Only argument parsing is exercised here, mirroring
tests/payments/test_reconciliation_cli.py: `main()` opens a session against
the configured database directly (not the isolated per-test transaction
other tests use), so the actual queue logic is tested through
`process_due_jobs`/`requeue_stuck_jobs` in test_jobs_queue.py instead."""

from app.cli.process_ai_jobs import build_arg_parser


def test_default_arguments() -> None:
    args = build_arg_parser().parse_args([])
    assert args.limit == 20
    assert args.stuck_after_seconds is None
    assert args.dry_run is False


def test_accepts_limit_stuck_after_seconds_and_dry_run_flags() -> None:
    args = build_arg_parser().parse_args(
        ["--limit", "5", "--stuck-after-seconds", "600", "--dry-run"]
    )
    assert args.limit == 5
    assert args.stuck_after_seconds == 600
    assert args.dry_run is True
