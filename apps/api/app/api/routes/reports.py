"""Reporting a design or a user — see docs/community-and-trust.md#5.
Reporting a message lives in app/api/routes/messaging.py (Phase 14);
reporting a comment lives in app/api/routes/comments.py — both reuse the
same app/services/reports.py::create_report() this module calls too.
"""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, limiter
from app.core.config import get_settings
from app.db.models.moderation import Report
from app.db.session import get_db_session
from app.schemas.moderation import ReportCreateRequest, ReportOut
from app.services.reports import create_report

router = APIRouter(tags=["reports"])


def _rate_limit() -> str:
    return get_settings().report_rate_limit


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


@router.post("/designs/{design_id}/report", response_model=ReportOut, status_code=201)
@limiter.limit(_rate_limit())
def report_design(
    request: Request,
    design_id: uuid.UUID,
    payload: ReportCreateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ReportOut:
    report = create_report(
        db,
        reporter_id=current.user.id,
        entity_type="design",
        entity_id=design_id,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(report)
    return _report_out(report)


@router.post("/users/{user_id}/report", response_model=ReportOut, status_code=201)
@limiter.limit(_rate_limit())
def report_user(
    request: Request,
    user_id: uuid.UUID,
    payload: ReportCreateRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ReportOut:
    report = create_report(
        db,
        reporter_id=current.user.id,
        entity_type="user",
        entity_id=user_id,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(report)
    return _report_out(report)
