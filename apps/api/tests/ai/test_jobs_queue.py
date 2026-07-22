"""The background job queue — see docs/ai-foundation.md#background-job-
processing. Exercises `app/services/ai/jobs.py` directly (enqueue, claim,
complete, fail/backoff, max-attempts exhaustion, and the stuck-job
requeue backstop)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.enums import AiGenerationStatus, AiJobStatus
from app.db.models.ai import AiJob
from app.services.ai.jobs import (
    claim_due_jobs,
    complete_job,
    count_pending_ai_jobs,
    enqueue_job,
    fail_job,
    process_due_jobs,
    register_handler,
    requeue_stuck_jobs,
)
from tests.db.factories import make_ai_generation, make_ai_job


def test_enqueue_job_creates_a_pending_row_due_immediately(db_session: Session) -> None:
    generation = make_ai_generation(db_session)
    job = enqueue_job(
        db_session, generation=generation, job_type="embedding_generation", payload={"a": 1}
    )
    db_session.commit()

    assert job.status == AiJobStatus.PENDING.value
    assert job.attempt_count == 0
    assert job.next_run_at <= datetime.now(UTC) + timedelta(seconds=1)


def test_claim_due_jobs_only_claims_pending_jobs_due_now(db_session: Session) -> None:
    due = make_ai_job(db_session, status=AiJobStatus.PENDING.value)
    not_due = make_ai_job(
        db_session,
        status=AiJobStatus.PENDING.value,
        next_run_at=datetime.now(UTC) + timedelta(hours=1),
    )
    already_running = make_ai_job(db_session, status=AiJobStatus.RUNNING.value)
    db_session.commit()

    claimed = claim_due_jobs(db_session, limit=20)
    claimed_ids = {j.id for j in claimed}

    assert due.id in claimed_ids
    assert not_due.id not in claimed_ids
    assert already_running.id not in claimed_ids

    refreshed = db_session.get(AiJob, due.id)
    assert refreshed is not None
    assert refreshed.status == AiJobStatus.RUNNING.value
    assert refreshed.attempt_count == 1
    assert refreshed.started_at is not None


def test_complete_job_marks_job_and_generation_completed(db_session: Session) -> None:
    generation = make_ai_generation(db_session, status=AiGenerationStatus.PROCESSING.value)
    job = make_ai_job(db_session, generation=generation, status=AiJobStatus.RUNNING.value)
    db_session.commit()

    complete_job(db_session, job, result={"dimension": 112})
    db_session.commit()

    assert job.status == AiJobStatus.COMPLETED.value
    assert job.completed_at is not None
    db_session.refresh(generation)
    assert generation.status == AiGenerationStatus.COMPLETED.value
    assert generation.response_payload == {"dimension": 112}


def test_fail_job_retries_with_backoff_when_attempts_remain(db_session: Session) -> None:
    job = make_ai_job(db_session, status=AiJobStatus.RUNNING.value, attempt_count=1, max_attempts=3)
    db_session.commit()

    fail_job(db_session, job, error="temporary provider error")
    db_session.commit()

    assert job.status == AiJobStatus.PENDING.value
    assert job.last_error == "temporary provider error"
    assert job.next_run_at > datetime.now(UTC)


def test_fail_job_terminally_fails_generation_once_attempts_exhausted(db_session: Session) -> None:
    generation = make_ai_generation(db_session, status=AiGenerationStatus.PROCESSING.value)
    job = make_ai_job(
        db_session,
        generation=generation,
        status=AiJobStatus.RUNNING.value,
        attempt_count=3,
        max_attempts=3,
    )
    db_session.commit()

    fail_job(db_session, job, error="permanent provider error")
    db_session.commit()

    assert job.status == AiJobStatus.FAILED.value
    assert job.completed_at is not None
    db_session.refresh(generation)
    assert generation.status == AiGenerationStatus.FAILED.value
    assert generation.error_message == "permanent provider error"


def test_fail_job_sends_an_ai_provider_failure_alert_once_exhausted(
    db_session: Session, monkeypatch
) -> None:
    """See docs/observability.md#ai-provider-failure-alerts."""
    import app.services.ai.jobs as jobs_module

    sent: list[str] = []
    monkeypatch.setattr(jobs_module, "send_alert", lambda event, **details: sent.append(event))

    generation = make_ai_generation(db_session, status=AiGenerationStatus.PROCESSING.value)
    job = make_ai_job(
        db_session,
        generation=generation,
        status=AiJobStatus.RUNNING.value,
        attempt_count=3,
        max_attempts=3,
    )
    db_session.commit()

    fail_job(db_session, job, error="permanent provider error")

    assert sent == ["ai_job_permanently_failed"]


def test_fail_job_does_not_alert_while_retries_remain(db_session: Session, monkeypatch) -> None:
    import app.services.ai.jobs as jobs_module

    sent: list[str] = []
    monkeypatch.setattr(jobs_module, "send_alert", lambda event, **details: sent.append(event))

    generation = make_ai_generation(db_session, status=AiGenerationStatus.PROCESSING.value)
    job = make_ai_job(
        db_session,
        generation=generation,
        status=AiJobStatus.RUNNING.value,
        attempt_count=1,
        max_attempts=3,
    )
    db_session.commit()

    fail_job(db_session, job, error="transient error")

    assert sent == []


def test_count_pending_ai_jobs_only_counts_pending_status(db_session: Session) -> None:
    make_ai_job(db_session, status=AiJobStatus.PENDING.value)
    make_ai_job(db_session, status=AiJobStatus.PENDING.value)
    make_ai_job(db_session, status=AiJobStatus.RUNNING.value)
    make_ai_job(db_session, status=AiJobStatus.COMPLETED.value)
    db_session.commit()

    assert count_pending_ai_jobs(db_session) >= 2


def test_process_due_jobs_dispatches_to_the_registered_handler(db_session: Session) -> None:
    calls: list[str] = []

    def _dummy_handler(session: Session, job: AiJob) -> dict[str, int]:
        calls.append(str(job.id))
        return {"ok": 1}

    register_handler("test_dummy_success", _dummy_handler)
    job = make_ai_job(db_session, job_type="test_dummy_success")
    db_session.commit()

    summary = process_due_jobs(db_session, limit=10)

    assert str(job.id) in calls
    assert summary.claimed >= 1
    assert summary.completed >= 1
    refreshed = db_session.get(AiJob, job.id)
    assert refreshed is not None
    assert refreshed.status == AiJobStatus.COMPLETED.value


def test_process_due_jobs_fails_the_job_when_the_handler_raises(db_session: Session) -> None:
    def _dummy_handler(session: Session, job: AiJob) -> dict[str, int]:
        raise RuntimeError("boom")

    register_handler("test_dummy_raises", _dummy_handler)
    job = make_ai_job(db_session, job_type="test_dummy_raises", max_attempts=1)
    db_session.commit()

    process_due_jobs(db_session, limit=10)

    refreshed = db_session.get(AiJob, job.id)
    assert refreshed is not None
    assert refreshed.status == AiJobStatus.FAILED.value
    assert refreshed.last_error is not None and "boom" in refreshed.last_error


def test_process_due_jobs_fails_a_job_with_no_registered_handler(db_session: Session) -> None:
    job = make_ai_job(db_session, job_type="totally_unknown_job_type", max_attempts=1)
    db_session.commit()

    process_due_jobs(db_session, limit=10)

    refreshed = db_session.get(AiJob, job.id)
    assert refreshed is not None
    assert refreshed.status == AiJobStatus.FAILED.value
    assert refreshed.last_error is not None and "No handler registered" in refreshed.last_error


def test_requeue_stuck_jobs_resets_a_job_whose_worker_died(db_session: Session) -> None:
    stuck_started_at = datetime.now(UTC) - timedelta(seconds=600)
    job = make_ai_job(
        db_session,
        status=AiJobStatus.RUNNING.value,
        attempt_count=1,
        max_attempts=3,
        started_at=stuck_started_at,
    )
    db_session.commit()

    changed = requeue_stuck_jobs(db_session, stuck_after_seconds=300)
    db_session.commit()

    assert changed == 1
    refreshed = db_session.get(AiJob, job.id)
    assert refreshed is not None
    assert refreshed.status == AiJobStatus.PENDING.value


def test_requeue_stuck_jobs_ignores_jobs_still_within_the_window(db_session: Session) -> None:
    job = make_ai_job(
        db_session,
        status=AiJobStatus.RUNNING.value,
        started_at=datetime.now(UTC) - timedelta(seconds=10),
    )
    db_session.commit()

    changed = requeue_stuck_jobs(db_session, stuck_after_seconds=300)

    assert changed == 0
    refreshed = db_session.get(AiJob, job.id)
    assert refreshed is not None
    assert refreshed.status == AiJobStatus.RUNNING.value
