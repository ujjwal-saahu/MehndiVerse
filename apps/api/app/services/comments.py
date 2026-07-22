"""Design comments and replies — see docs/community-and-trust.md#1-design-
comments-and-replies.

Replies are flattened to two levels: a reply's `parent_comment_id` must
point at a *top-level* comment (one whose own `parent_comment_id` is null),
not at another reply — see docs/community-and-trust.md#2-comment-replies-
are-flat.
"""

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, AuthorizationError
from app.db.enums import DesignStatus
from app.db.models.artist import ArtistProfile
from app.db.models.design import Design
from app.db.models.engagement import Comment
from app.services.blocking import is_blocked_either_direction

MAX_COMMENT_BODY_LENGTH = 2000

# Plain text only — same rationale as
# app/services/messaging.py::sanitize_message_body: strip HTML-tag-looking
# sequences at write time rather than store HTML-escaped text, so there's
# never an ambiguity about whether a stored body needs escaping again at
# render time.
_HTML_TAG_RE = re.compile(r"<[^>]*>")


def sanitize_comment_body(text: str) -> str:
    return _HTML_TAG_RE.sub("", text).strip()


def create_comment(
    db: Session,
    *,
    design: Design,
    user_id: uuid.UUID,
    body: str,
    parent_comment_id: uuid.UUID | None,
) -> Comment:
    if design.status != DesignStatus.PUBLISHED.value:
        raise AppError("You can only comment on a published design.", status_code=422)

    clean_body = sanitize_comment_body(body)
    if not clean_body:
        raise AppError("A comment needs some text.", status_code=422)
    if len(clean_body) > MAX_COMMENT_BODY_LENGTH:
        raise AppError(
            f"Comments cannot exceed {MAX_COMMENT_BODY_LENGTH} characters.", status_code=422
        )

    if parent_comment_id is not None:
        parent = db.get(Comment, parent_comment_id)
        if parent is None or parent.deleted_at is not None or parent.design_id != design.id:
            raise AppError("The comment you're replying to could not be found.", status_code=404)
        if parent.parent_comment_id is not None:
            raise AppError(
                "You can only reply to a top-level comment, not to another reply.",
                status_code=422,
            )

    if design.artist_profile_id is not None:
        artist_profile = db.get(ArtistProfile, design.artist_profile_id)
        if artist_profile is not None and is_blocked_either_direction(
            db, user_id, artist_profile.user_id
        ):
            raise AppError(
                "You can't comment on this design — one of you has blocked the other.",
                status_code=403,
            )

    comment = Comment(
        design_id=design.id,
        user_id=user_id,
        parent_comment_id=parent_comment_id,
        body=clean_body,
    )
    db.add(comment)
    db.flush()
    return comment


def list_top_level_comments(db: Session, design_id: uuid.UUID, *, limit: int = 20) -> list[Comment]:
    return list(
        db.execute(
            select(Comment)
            .where(
                Comment.design_id == design_id,
                Comment.parent_comment_id.is_(None),
                Comment.deleted_at.is_(None),
            )
            .order_by(Comment.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )


def list_replies(db: Session, parent_comment_id: uuid.UUID) -> list[Comment]:
    return list(
        db.execute(
            select(Comment)
            .where(Comment.parent_comment_id == parent_comment_id, Comment.deleted_at.is_(None))
            .order_by(Comment.created_at.asc())
        )
        .scalars()
        .all()
    )


def _require_owner(comment: Comment, user_id: uuid.UUID) -> None:
    if comment.user_id != user_id:
        raise AuthorizationError("You can only edit or delete your own comment.")


def update_comment(db: Session, comment: Comment, *, user_id: uuid.UUID, body: str) -> None:
    _require_owner(comment, user_id)
    if comment.deleted_at is not None:
        raise AppError("This comment has been deleted.", status_code=422)
    clean_body = sanitize_comment_body(body)
    if not clean_body:
        raise AppError("A comment needs some text.", status_code=422)
    if len(clean_body) > MAX_COMMENT_BODY_LENGTH:
        raise AppError(
            f"Comments cannot exceed {MAX_COMMENT_BODY_LENGTH} characters.", status_code=422
        )
    comment.body = clean_body
    db.add(comment)


def soft_delete_comment(db: Session, comment: Comment, *, user_id: uuid.UUID) -> None:
    """Soft-delete only — never hard-delete — so the body remains available
    as moderation evidence for any open report against this comment (see
    app/services/reports.py::entity_snapshot) even after the author "deletes"
    it. Replies are left untouched (the model's own docstring: "soft-deleted
    so threaded replies survive a parent comment's removal")."""
    _require_owner(comment, user_id)
    if comment.deleted_at is not None:
        return  # already deleted — idempotent no-op
    comment.deleted_at = datetime.now(UTC)
    db.add(comment)
