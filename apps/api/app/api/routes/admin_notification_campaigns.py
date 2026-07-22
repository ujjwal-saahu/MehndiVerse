"""Staff-side bulk notification campaigns — see docs/admin-dashboard.md
#notification-campaigns. Brand-new domain this phase. A campaign is drafted,
then sent once — sending fans out via the existing per-user
`notify_user()` to every active user matching `target_role` (or everyone,
if unset), synchronously, since no task-queue infrastructure exists in this
environment (same caveat as the booking-reminder foundation — see
docs/booking-messaging.md#3d).
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.admin_listing import normalize_pagination, paginate
from app.core.exceptions import AppError
from app.db.enums import NotificationType, UserRole, UserStatus
from app.db.models.promotions import NotificationCampaign
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminPageInfo,
    NotificationCampaignCreateRequest,
    NotificationCampaignListOut,
    NotificationCampaignOut,
)
from app.services.notifications import notify_user

router = APIRouter(prefix="/admin/notification-campaigns", tags=["admin-notification-campaigns"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")
_EDIT_ROLES = ("admin", "super_admin")

_VALID_TARGET_ROLES = {r.value for r in UserRole}


def _campaign_out(campaign: NotificationCampaign) -> NotificationCampaignOut:
    return NotificationCampaignOut(
        id=campaign.id,
        title=campaign.title,
        body=campaign.body,
        target_role=campaign.target_role,
        status=campaign.status,
        recipient_count=campaign.recipient_count,
        sent_at=campaign.sent_at,
        created_at=campaign.created_at,
    )


def _get_campaign_or_404(db: Session, campaign_id: uuid.UUID) -> NotificationCampaign:
    campaign = db.get(NotificationCampaign, campaign_id)
    if campaign is None:
        raise AppError("Notification campaign not found.", status_code=404)
    return campaign


@router.get("", response_model=NotificationCampaignListOut)
def list_campaigns(
    page: int = 1,
    page_size: int = 20,
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> NotificationCampaignListOut:
    page, page_size = normalize_pagination(page, page_size)
    stmt = select(NotificationCampaign).order_by(NotificationCampaign.created_at.desc())
    result = paginate(db, stmt, page=page, page_size=page_size)
    return NotificationCampaignListOut(
        items=[_campaign_out(c) for c in result.items],
        page_info=AdminPageInfo(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )


@router.post("", response_model=NotificationCampaignOut, status_code=201)
def create_campaign(
    payload: NotificationCampaignCreateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> NotificationCampaignOut:
    if payload.target_role is not None and payload.target_role not in _VALID_TARGET_ROLES:
        raise AppError(f"Unknown target_role: {payload.target_role}", status_code=422)

    campaign = NotificationCampaign(
        title=payload.title,
        body=payload.body,
        target_role=payload.target_role,
        status="draft",
        created_by=current.user.id,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return _campaign_out(campaign)


@router.post("/{campaign_id}/send", response_model=NotificationCampaignOut)
def send_campaign(
    campaign_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_EDIT_ROLES)),
    db: Session = Depends(get_db_session),
) -> NotificationCampaignOut:
    campaign = _get_campaign_or_404(db, campaign_id)
    if campaign.status == "sent":
        raise AppError("This campaign has already been sent.", status_code=422)

    stmt = select(User.id).where(User.deleted_at.is_(None), User.status == UserStatus.ACTIVE.value)
    if campaign.target_role is not None:
        stmt = stmt.where(User.role == campaign.target_role)
    recipient_ids = db.execute(stmt).scalars().all()

    for user_id in recipient_ids:
        notify_user(
            db,
            user_id=user_id,
            notification_type=NotificationType.MARKETING.value,
            title=campaign.title,
            body=campaign.body,
        )

    campaign.status = "sent"
    campaign.recipient_count = len(recipient_ids)
    campaign.sent_at = datetime.now(UTC)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return _campaign_out(campaign)
