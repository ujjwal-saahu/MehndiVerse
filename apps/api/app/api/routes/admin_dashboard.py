"""Admin dashboard overview — see docs/admin-dashboard.md#dashboard-
overview. One aggregate-counts endpoint rather than making the dashboard
home page fire off eight separate list calls just to show numbers.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.db.enums import ArtistVerificationStatus, BookingStatus, RefundStatus, ReportStatus
from app.db.models.artist import ArtistProfile
from app.db.models.booking import Booking
from app.db.models.design import Design
from app.db.models.moderation import Report
from app.db.models.payment import Refund
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.admin import DashboardOverviewOut

router = APIRouter(prefix="/admin/dashboard", tags=["admin-dashboard"])

_VIEW_ROLES = ("moderator", "admin", "super_admin")


@router.get("/overview", response_model=DashboardOverviewOut)
def get_dashboard_overview(
    current: AuthenticatedUser = Depends(require_roles(*_VIEW_ROLES)),
    db: Session = Depends(get_db_session),
) -> DashboardOverviewOut:
    pending_artist_verifications = db.execute(
        select(func.count())
        .select_from(ArtistProfile)
        .where(
            ArtistProfile.verification_status.in_(
                [
                    ArtistVerificationStatus.SUBMITTED.value,
                    ArtistVerificationStatus.UNDER_REVIEW.value,
                ]
            ),
            ArtistProfile.deleted_at.is_(None),
        )
    ).scalar_one()

    pending_reports = db.execute(
        select(func.count()).select_from(Report).where(Report.status == ReportStatus.PENDING.value)
    ).scalar_one()

    pending_refunds = db.execute(
        select(func.count()).select_from(Refund).where(Refund.status == RefundStatus.PENDING.value)
    ).scalar_one()

    disputed_bookings = db.execute(
        select(func.count())
        .select_from(Booking)
        .where(Booking.status == BookingStatus.DISPUTED.value)
    ).scalar_one()

    total_users = db.execute(
        select(func.count()).select_from(User).where(User.deleted_at.is_(None))
    ).scalar_one()

    total_artists = db.execute(
        select(func.count()).select_from(ArtistProfile).where(ArtistProfile.deleted_at.is_(None))
    ).scalar_one()

    total_designs = db.execute(
        select(func.count()).select_from(Design).where(Design.deleted_at.is_(None))
    ).scalar_one()

    total_bookings = db.execute(select(func.count()).select_from(Booking)).scalar_one()

    return DashboardOverviewOut(
        pending_artist_verifications=pending_artist_verifications,
        pending_reports=pending_reports,
        pending_refunds=pending_refunds,
        disputed_bookings=disputed_bookings,
        total_users=total_users,
        total_artists=total_artists,
        total_designs=total_designs,
        total_bookings=total_bookings,
    )
