"""Artist-side booking inbox, review, quoting, and calendar — see
docs/booking-lifecycle.md. Open to any `artist`/`verified_artist` (not gated
on verification status), matching app/api/routes/artist_scheduling.py's
precedent. Booking *detail* and the shared cancel/reschedule actions live in
app/api/routes/bookings.py (reachable by either party); this router only
holds actions that are specifically the artist's to take.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, require_roles
from app.core.exceptions import AppError, AuthorizationError
from app.db.enums import BOOKING_OCCUPYING_STATUS_VALUES, BookingStatus
from app.db.models.artist import ArtistProfile
from app.db.models.booking import Booking
from app.db.session import get_db_session
from app.schemas.booking import BookingDetailOut, BookingSummaryOut, QuoteCreateRequest
from app.services.booking import send_quote, start_artist_review
from app.services.booking_summaries import booking_detail, booking_summaries

router = APIRouter(prefix="/artist/bookings", tags=["artist-bookings"])

_SCHEDULING_ROLES = ("artist", "verified_artist")
_MAX_CALENDAR_RANGE_DAYS = 60


def _get_own_profile_or_404(db: Session, current: AuthenticatedUser) -> ArtistProfile:
    profile = db.execute(
        select(ArtistProfile).where(
            ArtistProfile.user_id == current.user.id, ArtistProfile.deleted_at.is_(None)
        )
    ).scalar_one_or_none()
    if profile is None:
        raise AppError("You need an artist profile before managing bookings.", status_code=404)
    return profile


def _get_own_booking_or_404(db: Session, booking_id: uuid.UUID, profile: ArtistProfile) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None or booking.status == BookingStatus.DRAFT.value:
        raise AppError("Booking not found.", status_code=404)
    if booking.artist_profile_id != profile.id:
        raise AuthorizationError("You do not have access to this booking.")
    return booking


@router.get("", response_model=list[BookingSummaryOut])
def list_my_booking_inbox(
    status_filter: str | None = None,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> list[BookingSummaryOut]:
    profile = _get_own_profile_or_404(db, current)
    stmt = select(Booking).where(
        Booking.artist_profile_id == profile.id, Booking.status != BookingStatus.DRAFT.value
    )
    if status_filter is not None:
        valid_statuses = {member.value for member in BookingStatus} - {BookingStatus.DRAFT.value}
        if status_filter not in valid_statuses:
            raise AppError(f"Unknown status: {status_filter}", status_code=422)
        stmt = stmt.where(Booking.status == status_filter)
    stmt = stmt.order_by(Booking.created_at.desc()).limit(200)
    bookings = list(db.execute(stmt).scalars().all())
    return booking_summaries(db, bookings)


@router.get("/calendar", response_model=list[BookingSummaryOut])
def get_my_booking_calendar(
    start_date: date,
    end_date: date,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> list[BookingSummaryOut]:
    profile = _get_own_profile_or_404(db, current)
    if end_date < start_date:
        raise AppError("end_date must be on or after start_date.", status_code=422)
    if (end_date - start_date).days + 1 > _MAX_CALENDAR_RANGE_DAYS:
        raise AppError(
            f"Date range cannot exceed {_MAX_CALENDAR_RANGE_DAYS} days.", status_code=422
        )
    stmt = (
        select(Booking)
        .where(
            Booking.artist_profile_id == profile.id,
            Booking.requested_date >= start_date,
            Booking.requested_date <= end_date,
            Booking.status.in_(BOOKING_OCCUPYING_STATUS_VALUES),
        )
        .order_by(Booking.requested_date, Booking.requested_time)
    )
    bookings = list(db.execute(stmt).scalars().all())
    return booking_summaries(db, bookings)


@router.post("/{booking_id}/review", response_model=BookingDetailOut)
def start_reviewing_booking(
    booking_id: uuid.UUID,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> BookingDetailOut:
    profile = _get_own_profile_or_404(db, current)
    booking = _get_own_booking_or_404(db, booking_id, profile)
    start_artist_review(db, booking, changed_by=current.user.id)
    db.commit()
    db.refresh(booking)
    return booking_detail(db, booking)


@router.post("/{booking_id}/quotes", response_model=BookingDetailOut, status_code=201)
def send_booking_quote(
    booking_id: uuid.UUID,
    payload: QuoteCreateRequest,
    current: AuthenticatedUser = Depends(require_roles(*_SCHEDULING_ROLES)),
    db: Session = Depends(get_db_session),
) -> BookingDetailOut:
    profile = _get_own_profile_or_404(db, current)
    booking = _get_own_booking_or_404(db, booking_id, profile)
    send_quote(
        db,
        booking,
        amount=payload.amount,
        currency=payload.currency,
        terms=payload.terms,
        valid_until=payload.valid_until,
        changed_by=current.user.id,
    )
    db.commit()
    db.refresh(booking)
    return booking_detail(db, booking)
