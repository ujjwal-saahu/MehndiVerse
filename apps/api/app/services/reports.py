"""Shared report creation and moderation-queue resolution — see
docs/community-and-trust.md#5-reports-enter-a-moderation-queue.

One `create_report()` backs every "report X" surface (design, comment,
user, and — from Phase 14 — message), so the abuse-prevention rule (no two
concurrently-open reports from the same reporter against the same target)
and the "must enter a moderation queue" rule (every report starts
`pending`, no auto-resolution) are enforced in exactly one place.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.enums import ReportEntityType, ReportStatus
from app.db.models.design import Design
from app.db.models.engagement import Comment
from app.db.models.messaging import Message
from app.db.models.moderation import Report
from app.db.models.user import Profile, User

MAX_REASON_LENGTH = 1000


def _entity_exists(db: Session, entity_type: str, entity_id: uuid.UUID) -> bool:
    if entity_type == ReportEntityType.DESIGN.value:
        return db.get(Design, entity_id) is not None
    if entity_type == ReportEntityType.COMMENT.value:
        # Deliberately not filtered by deleted_at — a soft-deleted comment
        # can still be reported/looked up for moderation purposes.
        return db.get(Comment, entity_id) is not None
    if entity_type == ReportEntityType.MESSAGE.value:
        return db.get(Message, entity_id) is not None
    if entity_type == ReportEntityType.USER.value:
        return db.get(User, entity_id) is not None
    return False


def create_report(
    db: Session, *, reporter_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID, reason: str
) -> Report:
    if entity_type == ReportEntityType.USER.value and entity_id == reporter_id:
        raise AppError("You cannot report yourself.", status_code=422)
    if not _entity_exists(db, entity_type, entity_id):
        raise AppError("The thing you're trying to report could not be found.", status_code=404)

    existing_pending = db.execute(
        select(Report.id).where(
            Report.reporter_id == reporter_id,
            Report.reported_entity_type == entity_type,
            Report.reported_entity_id == entity_id,
            Report.status == ReportStatus.PENDING.value,
        )
    ).first()
    if existing_pending is not None:
        raise AppError(
            "You already have an open report for this — no need to report it again.",
            status_code=409,
        )

    report = Report(
        reporter_id=reporter_id,
        reported_entity_type=entity_type,
        reported_entity_id=entity_id,
        reason=reason,
        status=ReportStatus.PENDING.value,
    )
    db.add(report)
    db.flush()
    return report


def resolve_report(
    db: Session, report: Report, *, resolved_by: uuid.UUID, resolution_notes: str | None
) -> None:
    if report.status not in (ReportStatus.PENDING.value, ReportStatus.REVIEWING.value):
        raise AppError("This report has already been closed.", status_code=422)
    report.status = ReportStatus.RESOLVED.value
    report.resolution_notes = resolution_notes
    report.resolved_by = resolved_by
    report.resolved_at = datetime.now(UTC)
    db.add(report)


def dismiss_report(
    db: Session, report: Report, *, resolved_by: uuid.UUID, resolution_notes: str | None
) -> None:
    if report.status not in (ReportStatus.PENDING.value, ReportStatus.REVIEWING.value):
        raise AppError("This report has already been closed.", status_code=422)
    report.status = ReportStatus.DISMISSED.value
    report.resolution_notes = resolution_notes
    report.resolved_by = resolved_by
    report.resolved_at = datetime.now(UTC)
    db.add(report)


def entity_snapshot(db: Session, report: Report) -> dict[str, Any] | None:
    """A read-time snapshot of the reported entity's current state,
    regardless of whether it's since been soft-deleted — this is the
    concrete mechanism behind "deleting comments must preserve moderation
    evidence": a user deleting their own comment only soft-deletes it (see
    app/services/comments.py), so staff reviewing a report against it can
    still see exactly what was reported here."""
    entity_type = report.reported_entity_type
    entity_id = report.reported_entity_id

    if entity_type == ReportEntityType.DESIGN.value:
        design = db.get(Design, entity_id)
        if design is None:
            return None
        return {"title": design.title, "status": design.status}

    if entity_type == ReportEntityType.COMMENT.value:
        comment = db.get(Comment, entity_id)
        if comment is None:
            return None
        return {
            "body": comment.body,
            "design_id": str(comment.design_id),
            "is_deleted": comment.deleted_at is not None,
        }

    if entity_type == ReportEntityType.USER.value:
        profile = db.execute(
            select(Profile.display_name).where(Profile.user_id == entity_id)
        ).scalar_one_or_none()
        return {"display_name": profile}

    if entity_type == ReportEntityType.MESSAGE.value:
        message = db.get(Message, entity_id)
        if message is None:
            return None
        return {"body": message.body, "is_deleted": message.deleted_at is not None}

    return None
