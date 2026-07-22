"""Staff-side moderation queue — see
docs/community-and-trust.md#5-reports-enter-a-moderation-queue.

Viewing the queue is available to `moderator`, `admin`, and `super_admin`
(mirrors app/api/routes/admin_artist_verification.py's `_VIEW_ROLES`); only
`admin`/`super_admin` may resolve or dismiss a report (`_EDIT_ROLES`) — the
same split established there. Resolving/dismissing is deliberately
record-keeping only (status + resolution_notes + who/when) — it does not
auto-delete comments, auto-suspend users, or auto-unpublish designs. Staff
take those actions through the existing dedicated surfaces (comment
delete, admin_users.py, designs.py moderation) after reviewing the report;
this keeps "reports enter a moderation queue" from silently growing into
an auto-moderation system.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import literal, select, tuple_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.exceptions import AppError
from app.core.pagination import InvalidCursorError, decode_cursor, encode_cursor
from app.db.enums import ReportStatus
from app.db.models.moderation import Report
from app.db.session import get_db_session
from app.schemas.design import PageInfo
from app.schemas.moderation import (
    ReportOut,
    ReportQueueItemOut,
    ReportQueueOut,
    ReportResolutionRequest,
)
from app.services.reports import dismiss_report, entity_snapshot, resolve_report

router = APIRouter(prefix="/admin/reports", tags=["admin-moderation"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_EDIT_ROLES = ("admin", "super_admin")

_QUEUE_SORT = "moderation_queue"


def _get_report_or_404(db: Session, report_id: uuid.UUID) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise AppError("Report not found.", status_code=404)
    return report


def _queue_item_out(db: Session, report: Report) -> ReportQueueItemOut:
    return ReportQueueItemOut(
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
        entity_snapshot=entity_snapshot(db, report),
    )


def _report_out(report: Report) -> ReportOut:
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


@router.get("", response_model=ReportQueueOut)
def list_moderation_queue(
    status_filter: list[str] | None = Query(default=None),
    entity_type: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> ReportQueueOut:
    limit = max(1, min(limit, 100))
    statuses = status_filter or [ReportStatus.PENDING.value]
    unknown = set(statuses) - {member.value for member in ReportStatus}
    if unknown:
        raise AppError(f"Unknown status filter(s): {', '.join(sorted(unknown))}", status_code=422)

    stmt = select(Report).where(Report.status.in_(statuses))
    if entity_type is not None:
        stmt = stmt.where(Report.reported_entity_type == entity_type)
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor, expected_sort=_QUEUE_SORT)
        except InvalidCursorError as exc:
            raise AppError(str(exc), status_code=422) from exc
        cursor_created_at = datetime.fromisoformat(decoded.sort_value)
        stmt = stmt.where(
            tuple_(Report.created_at, Report.id)
            < tuple_(literal(cursor_created_at), literal(decoded.id))
        )
    stmt = stmt.order_by(Report.created_at.desc(), Report.id.desc()).limit(limit + 1)

    reports = list(db.execute(stmt).scalars().all())
    has_more = len(reports) > limit
    page = reports[:limit]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            sort=_QUEUE_SORT, sort_value=last.created_at.isoformat(), id_=last.id
        )

    return ReportQueueOut(
        items=[_queue_item_out(db, r) for r in page],
        page_info=PageInfo(next_cursor=next_cursor, has_more=has_more),
    )


@router.get("/{report_id}", response_model=ReportQueueItemOut)
def get_moderation_queue_item(
    report_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> ReportQueueItemOut:
    report = _get_report_or_404(db, report_id)
    return _queue_item_out(db, report)


@router.post("/{report_id}/resolve", response_model=ReportOut)
def resolve_moderation_report(
    report_id: uuid.UUID,
    payload: ReportResolutionRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> ReportOut:
    report = _get_report_or_404(db, report_id)
    resolve_report(
        db, report, resolved_by=current.user.id, resolution_notes=payload.resolution_notes
    )
    db.commit()
    db.refresh(report)
    return _report_out(report)


@router.post("/{report_id}/dismiss", response_model=ReportOut)
def dismiss_moderation_report(
    report_id: uuid.UUID,
    payload: ReportResolutionRequest,
    request: Request,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> ReportOut:
    report = _get_report_or_404(db, report_id)
    dismiss_report(
        db, report, resolved_by=current.user.id, resolution_notes=payload.resolution_notes
    )
    db.commit()
    db.refresh(report)
    return _report_out(report)
