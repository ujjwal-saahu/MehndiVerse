"""Batched DTO-building for booking list/detail responses — see
docs/booking-lifecycle.md. Mirrors app/services/artist_summaries.py's
"one query per lookup type, not per row" shape.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.artist import ArtistProfile, ArtistService
from app.db.models.booking import Booking, BookingAttachment, BookingQuote, BookingStatusHistory
from app.db.models.user import Profile
from app.schemas.booking import (
    BookingAttachmentOut,
    BookingDetailOut,
    BookingQuoteOut,
    BookingStatusHistoryOut,
    BookingSummaryOut,
)


def _artist_display_names(
    db: Session, artist_profile_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str | None]:
    if not artist_profile_ids:
        return {}
    rows = db.execute(
        select(
            ArtistProfile.id, ArtistProfile.professional_name, ArtistProfile.business_name
        ).where(ArtistProfile.id.in_(set(artist_profile_ids)))
    ).all()
    return {row.id: row.professional_name or row.business_name for row in rows}


def _customer_display_names(
    db: Session, customer_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str | None]:
    if not customer_ids:
        return {}
    rows = db.execute(
        select(Profile.user_id, Profile.display_name).where(Profile.user_id.in_(set(customer_ids)))
    ).all()
    return {row.user_id: row.display_name for row in rows}


def _service_names(db: Session, service_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not service_ids:
        return {}
    rows = db.execute(
        select(ArtistService.id, ArtistService.name).where(ArtistService.id.in_(set(service_ids)))
    ).all()
    return {row.id: row.name for row in rows}


def booking_summaries(db: Session, bookings: list[Booking]) -> list[BookingSummaryOut]:
    artist_names = _artist_display_names(db, [b.artist_profile_id for b in bookings])
    customer_names = _customer_display_names(db, [b.customer_id for b in bookings])
    service_names = _service_names(db, [b.service_id for b in bookings if b.service_id is not None])
    return [_summary(b, artist_names, customer_names, service_names) for b in bookings]


def _summary(
    booking: Booking,
    artist_names: dict[uuid.UUID, str | None],
    customer_names: dict[uuid.UUID, str | None],
    service_names: dict[uuid.UUID, str],
) -> BookingSummaryOut:
    return BookingSummaryOut(
        id=booking.id,
        artist_profile_id=booking.artist_profile_id,
        artist_display_name=artist_names.get(booking.artist_profile_id),
        customer_id=booking.customer_id,
        customer_display_name=customer_names.get(booking.customer_id),
        service_id=booking.service_id,
        service_name=service_names.get(booking.service_id) if booking.service_id else None,
        status=booking.status,
        requested_date=booking.requested_date,
        requested_time=booking.requested_time,
        location_type=booking.location_type,
        event_type=booking.event_type,
        num_customers=booking.num_customers,
        total_amount=booking.total_amount,
        currency=booking.currency,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
    )


def booking_detail(db: Session, booking: Booking) -> BookingDetailOut:
    summary = _summary(
        booking,
        _artist_display_names(db, [booking.artist_profile_id]),
        _customer_display_names(db, [booking.customer_id]),
        _service_names(db, [booking.service_id] if booking.service_id else []),
    )

    quotes = (
        db.execute(
            select(BookingQuote)
            .where(BookingQuote.booking_id == booking.id)
            .order_by(BookingQuote.created_at.desc())
        )
        .scalars()
        .all()
    )
    history = (
        db.execute(
            select(BookingStatusHistory)
            .where(BookingStatusHistory.booking_id == booking.id)
            .order_by(BookingStatusHistory.created_at.asc())
        )
        .scalars()
        .all()
    )
    attachments = (
        db.execute(
            select(BookingAttachment)
            .where(BookingAttachment.booking_id == booking.id)
            .order_by(BookingAttachment.created_at.asc())
        )
        .scalars()
        .all()
    )

    return BookingDetailOut(
        **summary.model_dump(),
        design_id=booking.design_id,
        location_address=booking.location_address,
        design_preferences=booking.design_preferences,
        notes=booking.notes,
        budget_min=booking.budget_min,
        budget_max=booking.budget_max,
        contact_name=booking.contact_name,
        contact_email=booking.contact_email,
        contact_phone=booking.contact_phone,
        deposit_amount=booking.deposit_amount,
        cancelled_by=booking.cancelled_by,
        cancellation_reason=booking.cancellation_reason,
        completed_at=booking.completed_at,
        cancelled_at=booking.cancelled_at,
        quotes=[
            BookingQuoteOut(
                id=q.id,
                amount=q.amount,
                currency=q.currency,
                terms=q.terms,
                valid_until=q.valid_until,
                status=q.status,
                created_at=q.created_at,
            )
            for q in quotes
        ],
        status_history=[
            BookingStatusHistoryOut(
                id=h.id,
                from_status=h.from_status,
                to_status=h.to_status,
                changed_by=h.changed_by,
                reason=h.reason,
                created_at=h.created_at,
            )
            for h in history
        ],
        attachments=[
            BookingAttachmentOut(
                id=a.id,
                file_url=a.file_url,
                file_type=a.file_type,
                caption=a.caption,
                uploaded_by=a.uploaded_by,
                created_at=a.created_at,
            )
            for a in attachments
        ],
    )
