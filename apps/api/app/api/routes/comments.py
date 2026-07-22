"""Design comments and replies — see docs/community-and-trust.md#1.

`/designs/{design_id}/comments` (create/list) lives here rather than in
app/api/routes/designs.py to keep that already-large file from growing
further — mirrors how booking messaging/payments got their own route
modules instead of extending bookings.py.
"""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, limiter
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.models.design import Design
from app.db.models.engagement import Comment
from app.db.models.user import Profile
from app.db.session import get_db_session
from app.schemas.comment import (
    CommentCreateRequest,
    CommentEditOut,
    CommentListOut,
    CommentOut,
    CommentUpdateRequest,
    ReplyOut,
)
from app.schemas.moderation import ReportCreateRequest, ReportOut
from app.services.comments import (
    create_comment,
    list_replies,
    list_top_level_comments,
    soft_delete_comment,
    update_comment,
)
from app.services.reports import create_report

router = APIRouter(tags=["comments"])


def _rate_limit() -> str:
    return get_settings().comment_rate_limit


def _report_rate_limit() -> str:
    return get_settings().report_rate_limit


def _get_design_or_404(db: Session, design_id: uuid.UUID) -> Design:
    design = db.get(Design, design_id)
    if design is None or design.deleted_at is not None:
        raise AppError("Design not found.", status_code=404)
    return design


def _get_comment_or_404(db: Session, comment_id: uuid.UUID) -> Comment:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise AppError("Comment not found.", status_code=404)
    return comment


def _display_names(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str | None]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(Profile.user_id, Profile.display_name).where(Profile.user_id.in_(set(user_ids)))
    ).all()
    return {row.user_id: row.display_name for row in rows}


def _reply_out(reply: Comment, names: dict[uuid.UUID, str | None]) -> ReplyOut:
    assert reply.parent_comment_id is not None
    return ReplyOut(
        id=reply.id,
        design_id=reply.design_id,
        user_id=reply.user_id,
        user_display_name=names.get(reply.user_id),
        parent_comment_id=reply.parent_comment_id,
        body=reply.body,
        created_at=reply.created_at,
        updated_at=reply.updated_at,
    )


def _comment_out(
    comment: Comment, replies: list[Comment], names: dict[uuid.UUID, str | None]
) -> CommentOut:
    return CommentOut(
        id=comment.id,
        design_id=comment.design_id,
        user_id=comment.user_id,
        user_display_name=names.get(comment.user_id),
        body=comment.body,
        replies=[_reply_out(r, names) for r in replies],
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.get("/designs/{design_id}/comments", response_model=CommentListOut)
def list_design_comments(
    design_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> CommentListOut:
    design = _get_design_or_404(db, design_id)
    top_level = list_top_level_comments(db, design.id)
    replies_by_parent = {c.id: list_replies(db, c.id) for c in top_level}
    all_user_ids = [c.user_id for c in top_level]
    for replies in replies_by_parent.values():
        all_user_ids.extend(r.user_id for r in replies)
    names = _display_names(db, all_user_ids)
    return CommentListOut(
        items=[_comment_out(c, replies_by_parent.get(c.id, []), names) for c in top_level]
    )


@router.post("/designs/{design_id}/comments", response_model=CommentOut, status_code=201)
@limiter.limit(_rate_limit())
def create_design_comment(
    request: Request,
    design_id: uuid.UUID,
    payload: CommentCreateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CommentOut:
    design = _get_design_or_404(db, design_id)
    comment = create_comment(
        db,
        design=design,
        user_id=current.user.id,
        body=payload.body,
        parent_comment_id=payload.parent_comment_id,
    )
    db.commit()
    db.refresh(comment)
    names = _display_names(db, [comment.user_id])
    return _comment_out(comment, [], names)


@router.patch("/comments/{comment_id}", response_model=CommentEditOut)
def edit_my_comment(
    comment_id: uuid.UUID,
    payload: CommentUpdateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CommentEditOut:
    comment = _get_comment_or_404(db, comment_id)
    update_comment(db, comment, user_id=current.user.id, body=payload.body)
    db.commit()
    db.refresh(comment)
    names = _display_names(db, [comment.user_id])
    return CommentEditOut(
        id=comment.id,
        design_id=comment.design_id,
        user_id=comment.user_id,
        user_display_name=names.get(comment.user_id),
        parent_comment_id=comment.parent_comment_id,
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.delete("/comments/{comment_id}", status_code=204)
def delete_my_comment(
    comment_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    comment = _get_comment_or_404(db, comment_id)
    soft_delete_comment(db, comment, user_id=current.user.id)
    db.commit()


@router.post("/comments/{comment_id}/report", response_model=ReportOut, status_code=201)
@limiter.limit(_report_rate_limit())
def report_comment(
    request: Request,
    comment_id: uuid.UUID,
    payload: ReportCreateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ReportOut:
    report = create_report(
        db,
        reporter_id=current.user.id,
        entity_type="comment",
        entity_id=comment_id,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(report)
    return ReportOut(
        id=report.id,
        reporter_id=report.reporter_id,
        reported_entity_type=report.reported_entity_type,
        reported_entity_id=report.reported_entity_id,
        status=report.status,
        reason=report.reason,
        resolution_notes=report.resolution_notes,
        resolved_by=report.resolved_by,
        resolved_at=report.resolved_at,
        created_at=report.created_at,
    )
