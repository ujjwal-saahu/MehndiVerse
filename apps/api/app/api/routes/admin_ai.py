"""Staff-side AI operations surface — see docs/ai-foundation.md#human-review
and #background-job-processing.

Mirrors `app/api/routes/admin_moderation.py`'s exact shape: `_VIEW_ROLES`
(moderator/admin/super_admin) may see the queues, only `_EDIT_ROLES`
(admin/super_admin) may resolve anything — reviewing an AI moderation flag
or a duplicate match is a moderation action, so it gets the same role split
reports do. Resolving is record-keeping only: it never itself unpublishes a
design or deletes anything — staff take that action through the existing
`designs.py`/`admin_users.py` surfaces after reviewing here, same
separation `admin_moderation.py`'s docstring establishes for reports.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import literal, select, tuple_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.exceptions import AppError
from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor
from app.db.enums import AiJobStatus, AiReviewStatus, DuplicateMatchStatus
from app.db.models.ai import AiGeneration, AiJob, DesignDuplicateMatch
from app.db.session import get_db_session
from app.schemas.ai import (
    AiDuplicateQueueOut,
    AiGenerationStatusOut,
    AiJobOut,
    AiReviewQueueOut,
    DuplicateMatchOut,
    ReviewResolutionRequest,
)
from app.schemas.design import PageInfo
from app.services.ai.review import resolve_duplicate_match, resolve_generation_review

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_EDIT_ROLES = ("admin", "super_admin")

_REVIEW_QUEUE_SORT = "ai_review_queue"
_DUPLICATE_QUEUE_SORT = "ai_duplicate_queue"


def _job_out(job: AiJob) -> AiJobOut:
    return AiJobOut(
        id=job.id,
        generation_id=job.generation_id,
        job_type=job.job_type,
        status=job.status,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        last_error=job.last_error,
        next_run_at=job.next_run_at,
        created_at=job.created_at,
    )


def _generation_status_out(generation: AiGeneration) -> AiGenerationStatusOut:
    return AiGenerationStatusOut(
        id=generation.id,
        generation_type=generation.generation_type,
        status=generation.status,
        provider=generation.provider,
        model_name=generation.model_name,
        confidence=generation.confidence,
        requires_human_review=generation.requires_human_review,
        review_status=generation.review_status,
        error_message=generation.error_message,
        created_at=generation.created_at,
        updated_at=generation.updated_at,
    )


def _duplicate_match_out(match: DesignDuplicateMatch) -> DuplicateMatchOut:
    return DuplicateMatchOut(
        id=match.id,
        design_id=match.design_id,
        matched_design_id=match.matched_design_id,
        similarity=match.similarity,
        status=match.status,
        created_at=match.created_at,
    )


@router.get("/jobs", response_model=list[AiJobOut])
def list_ai_jobs(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = 50,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> list[AiJobOut]:
    limit = max(1, min(limit, 200))
    stmt = select(AiJob)
    if status_filter is not None:
        if status_filter not in {member.value for member in AiJobStatus}:
            raise AppError(f"Unknown job status: {status_filter}", status_code=422)
        stmt = stmt.where(AiJob.status == status_filter)
    stmt = stmt.order_by(AiJob.created_at.desc()).limit(limit)
    jobs = db.execute(stmt).scalars().all()
    return [_job_out(j) for j in jobs]


@router.get("/review-queue", response_model=AiReviewQueueOut)
def list_review_queue(
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> AiReviewQueueOut:
    limit = max(1, min(limit, 100))
    stmt = select(AiGeneration).where(AiGeneration.review_status == AiReviewStatus.PENDING.value)
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_REVIEW_QUEUE_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_created_at = datetime.fromisoformat(decoded.sort_value)
        stmt = stmt.where(
            tuple_(AiGeneration.created_at, AiGeneration.id)
            < tuple_(literal(cursor_created_at), literal(decoded.id))
        )
    stmt = stmt.order_by(AiGeneration.created_at.desc(), AiGeneration.id.desc()).limit(limit + 1)
    generations = list(db.execute(stmt).scalars().all())
    has_more = len(generations) > limit
    page = generations[:limit]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            sort=_REVIEW_QUEUE_SORT, sort_value=last.created_at.isoformat(), id_=last.id
        )

    return AiReviewQueueOut(
        items=[_generation_status_out(g) for g in page],
        page_info=PageInfo(next_cursor=next_cursor, has_more=has_more),
    )


@router.post("/review-queue/{generation_id}/resolve", response_model=AiGenerationStatusOut)
def resolve_review_item(
    generation_id: uuid.UUID,
    payload: ReviewResolutionRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> AiGenerationStatusOut:
    generation = db.get(AiGeneration, generation_id)
    if generation is None:
        raise AppError("AI generation not found.", status_code=404)
    resolve_generation_review(
        db,
        generation,
        resolved_by=current.user.id,
        approved=payload.approved,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(generation)
    return _generation_status_out(generation)


@router.get("/duplicate-matches", response_model=AiDuplicateQueueOut)
def list_duplicate_matches(
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> AiDuplicateQueueOut:
    limit = max(1, min(limit, 100))
    stmt = select(DesignDuplicateMatch).where(
        DesignDuplicateMatch.status == DuplicateMatchStatus.PENDING.value
    )
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_DUPLICATE_QUEUE_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_created_at = datetime.fromisoformat(decoded.sort_value)
        stmt = stmt.where(
            tuple_(DesignDuplicateMatch.created_at, DesignDuplicateMatch.id)
            < tuple_(literal(cursor_created_at), literal(decoded.id))
        )
    stmt = stmt.order_by(
        DesignDuplicateMatch.created_at.desc(), DesignDuplicateMatch.id.desc()
    ).limit(limit + 1)
    matches = list(db.execute(stmt).scalars().all())
    has_more = len(matches) > limit
    page = matches[:limit]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            sort=_DUPLICATE_QUEUE_SORT, sort_value=last.created_at.isoformat(), id_=last.id
        )

    return AiDuplicateQueueOut(
        items=[_duplicate_match_out(m) for m in page],
        page_info=PageInfo(next_cursor=next_cursor, has_more=has_more),
    )


@router.post("/duplicate-matches/{match_id}/resolve", response_model=DuplicateMatchOut)
def resolve_duplicate_match_route(
    match_id: uuid.UUID,
    payload: ReviewResolutionRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> DuplicateMatchOut:
    match = db.get(DesignDuplicateMatch, match_id)
    if match is None:
        raise AppError("Duplicate match not found.", status_code=404)
    resolve_duplicate_match(db, match, resolved_by=current.user.id, confirmed=payload.approved)
    db.commit()
    db.refresh(match)
    return _duplicate_match_out(match)
