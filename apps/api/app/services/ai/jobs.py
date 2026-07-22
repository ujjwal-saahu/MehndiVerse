"""The background job queue — see docs/ai-foundation.md#background-job-
processing.

A plain database-table queue: `AiJob` rows are claimed with a `SELECT ...
FOR UPDATE SKIP LOCKED` + conditional `UPDATE ... WHERE status = 'pending'`
pair (`claim_due_jobs`), the same pattern any real job-queue library uses
internally — so this is retry-safe and concurrency-safe even with more
than one worker process running `python -m app.cli.process_ai_jobs`
simultaneously, without needing Celery/RQ/Redis-as-a-queue. Failed jobs are
retried with exponential backoff up to `max_attempts`, then left in a
terminal `failed` state — never silently dropped, never retried forever.

"AI calls must not block normal API workers" is satisfied by the queue's
existence, not by anything clever inside this module: a route only ever
calls `enqueue_job` (a fast INSERT) and returns — the actual provider work
happens in the *separate* `process_ai_jobs` worker process, which by
construction cannot block a request-handling worker. Timeouts are enforced
one layer down, at the network boundary
(`app/services/ai/imaging.py::fetch_image_bytes`'s `httpx` timeout) rather
than by wrapping handler execution in a thread here — an earlier version of
this module did exactly that, but a `Session` isn't safe to hand to a
worker thread while the request/CLI thread keeps using it, and Python
cannot forcibly cancel a running thread anyway. `requeue_stuck_jobs()`
below is the actual timeout backstop: if a worker process dies or hangs
mid-job, the job is left `running` with a `started_at` that ages past
`ai_job_stuck_after_seconds`, and the next `process_ai_jobs` invocation
(or a periodic one) resets it — the same "reconciliation" shape
`app/services/payments/service.py::reconcile_pending_payments` already
uses for exactly this class of problem (see docs/payments.md#10).
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.alerts import send_alert
from app.core.config import get_settings
from app.core.metrics import observe_dependency_failure
from app.db.enums import AiGenerationStatus, AiJobStatus
from app.db.models.ai import AiGeneration, AiJob

JobHandler = Callable[[Session, AiJob], dict[str, Any] | None]

_HANDLERS: dict[str, JobHandler] = {}

_BACKOFF_BASE_SECONDS = 60
_BACKOFF_MAX_SECONDS = 3600


def register_handler(job_type: str, handler: JobHandler) -> None:
    """Called once per job type by `app/services/ai/handlers.py` — never by
    application code directly. A plain dict registry (not a decorator on
    each capability module) keeps the import direction one-way: capability
    modules import `enqueue_job` from here, this module never imports them
    back, so there's no circular import to work around."""
    _HANDLERS[job_type] = handler


def enqueue_job(
    db: Session,
    *,
    generation: AiGeneration,
    job_type: str,
    payload: dict[str, Any],
    max_attempts: int | None = None,
) -> AiJob:
    job = AiJob(
        generation_id=generation.id,
        job_type=job_type,
        payload=payload,
        max_attempts=max_attempts or get_settings().ai_job_max_attempts,
    )
    db.add(job)
    db.flush()
    return job


def enqueue_design_ai_job(
    db: Session,
    *,
    design_id: uuid.UUID,
    generation_type: str,
    job_type: str,
    triggered_by: uuid.UUID | None = None,
    max_attempts: int | None = None,
) -> AiGeneration:
    """Shared by every capability whose job is "run against one design,
    payload is just `{"design_id": ...}`" — tagging, embeddings, moderation,
    and duplicate-detection all enqueued through this one function instead
    of each hand-rolling the same `AiGeneration` + `AiJob` pair. A capability
    module's own `enqueue_*` stays the public entry point (naming its own
    `generation_type`/`job_type`); this is only the shared plumbing beneath
    it."""
    generation = AiGeneration(
        user_id=triggered_by,
        generation_type=generation_type,
        entity_type="design",
        entity_id=design_id,
        request_payload={"design_id": str(design_id)},
    )
    db.add(generation)
    db.flush()
    enqueue_job(
        db,
        generation=generation,
        job_type=job_type,
        payload={"design_id": str(design_id)},
        max_attempts=max_attempts,
    )
    return generation


def claim_due_jobs(db: Session, *, limit: int = 20) -> list[AiJob]:
    now = datetime.now(UTC)
    candidate_ids = (
        db.execute(
            select(AiJob.id)
            .where(AiJob.status == AiJobStatus.PENDING.value, AiJob.next_run_at <= now)
            .order_by(AiJob.next_run_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        .scalars()
        .all()
    )
    if not candidate_ids:
        return []

    db.execute(
        update(AiJob)
        .where(AiJob.id.in_(candidate_ids), AiJob.status == AiJobStatus.PENDING.value)
        .values(
            status=AiJobStatus.RUNNING.value,
            started_at=now,
            attempt_count=AiJob.attempt_count + 1,
        )
    )
    db.commit()
    return list(db.execute(select(AiJob).where(AiJob.id.in_(candidate_ids))).scalars().all())


def complete_job(db: Session, job: AiJob, *, result: dict[str, Any] | None) -> None:
    job.status = AiJobStatus.COMPLETED.value
    job.completed_at = datetime.now(UTC)
    db.add(job)

    generation = db.get(AiGeneration, job.generation_id)
    if generation is not None:
        generation.status = AiGenerationStatus.COMPLETED.value
        if result is not None:
            generation.response_payload = result
        db.add(generation)


def fail_job(db: Session, job: AiJob, *, error: str) -> None:
    job.last_error = error[:2000]
    db.add(job)

    if job.attempt_count >= job.max_attempts:
        job.status = AiJobStatus.FAILED.value
        job.completed_at = datetime.now(UTC)
        generation = db.get(AiGeneration, job.generation_id)
        if generation is not None:
            generation.status = AiGenerationStatus.FAILED.value
            generation.error_message = error[:2000]
            db.add(generation)
        # AI-provider failure alert — see docs/observability.md#alerting.
        # Fires once, when a job is exhausted (permanently failed), not on
        # every retry attempt — a transient failure that succeeds on retry
        # was never alert-worthy.
        observe_dependency_failure("ai_provider")
        send_alert(
            "ai_job_permanently_failed",
            job_id=str(job.id),
            job_type=job.job_type,
            attempts=job.attempt_count,
            error=error[:500],
        )
    else:
        job.status = AiJobStatus.PENDING.value
        backoff_seconds = min(_BACKOFF_BASE_SECONDS * (2**job.attempt_count), _BACKOFF_MAX_SECONDS)
        job.next_run_at = datetime.now(UTC) + timedelta(seconds=backoff_seconds)


@dataclass(frozen=True)
class ProcessSummary:
    claimed: int
    completed: int
    failed: int


def count_pending_ai_jobs(db: Session) -> int:
    """Queue depth — see docs/observability.md#queue-depth. Recorded by
    app/cli/process_ai_jobs.py after each run; a number that keeps growing
    run over run means jobs are arriving faster than they're processed."""
    return db.execute(
        select(func.count()).select_from(AiJob).where(AiJob.status == AiJobStatus.PENDING.value)
    ).scalar_one()


def process_due_jobs(db: Session, *, limit: int = 20) -> ProcessSummary:
    """The worker entry point — `python -m app.cli.process_ai_jobs` calls
    this in a loop. No scheduler exists in this environment (same "no real
    background worker provisioned" constraint every other phase's queued
    work has — see docs/payments.md#10-reconciliation-command); this is a
    standalone, manually/externally-triggered command."""
    from app.services.ai import handlers as _handlers  # noqa: F401  (registers handlers)

    jobs = claim_due_jobs(db, limit=limit)
    completed = 0
    failed = 0

    for job in jobs:
        job_id = job.id
        job_type = job.job_type
        generation = db.get(AiGeneration, job.generation_id)
        if generation is not None:
            generation.status = AiGenerationStatus.PROCESSING.value
            db.add(generation)
            db.commit()

        handler = _HANDLERS.get(job_type)
        if handler is None:
            unhandled_job = db.get(AiJob, job_id)
            assert unhandled_job is not None
            fail_job(db, unhandled_job, error=f"No handler registered for job_type={job_type!r}.")
            db.commit()
            failed += 1
            continue

        try:
            result = handler(db, job)
        except Exception as exc:  # noqa: BLE001 - a handler failure must never crash the worker
            db.rollback()
            failed_job = db.get(AiJob, job_id)
            assert failed_job is not None
            fail_job(db, failed_job, error=str(exc)[:2000])
            db.commit()
            failed += 1
            continue

        completed_job = db.get(AiJob, job_id)
        assert completed_job is not None
        complete_job(db, completed_job, result=result)
        db.commit()
        completed += 1

    return ProcessSummary(claimed=len(jobs), completed=completed, failed=failed)


def requeue_stuck_jobs(db: Session, *, stuck_after_seconds: int | None = None) -> int:
    """The actual timeout backstop (see this module's docstring): a job
    left `running` past this age means its worker process died or hung
    mid-handler. Resets it to `pending` (or fails it outright if it's
    already exhausted its attempts) so a future worker picks it back up —
    exactly `reconcile_pending_payments`'s shape, applied to jobs instead
    of payments. Returns the number of jobs changed."""
    settings = get_settings()
    threshold_seconds = stuck_after_seconds or settings.ai_job_stuck_after_seconds
    cutoff = datetime.now(UTC) - timedelta(seconds=threshold_seconds)

    stuck = (
        db.execute(
            select(AiJob).where(
                AiJob.status == AiJobStatus.RUNNING.value, AiJob.started_at < cutoff
            )
        )
        .scalars()
        .all()
    )
    for job in stuck:
        fail_job(db, job, error=f"Worker did not report back within {threshold_seconds}s.")
    return len(stuck)
