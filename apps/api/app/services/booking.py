"""Booking lifecycle — see docs/booking-lifecycle.md.

`transition_booking()` is the *only* place `bookings.status` is written: it
validates the hop against `BOOKING_STATUS_TRANSITIONS`
(app/db/enums.py::is_valid_booking_transition) and records a
`booking_status_history` row in the same call, so the two can never drift.
Every higher-level action in this module (submit, send/accept/reject a
quote, cancel...) goes through it rather than assigning `booking.status`
directly. `record_history_note()` is the sibling for actions (reschedule)
that touch the audit trail without an actual status change — self-loops are
deliberately excluded from the transition table, so they're not valid
`transition_booking()` calls.

Payments are disabled this phase: `accept_quote()` can land a booking on
`deposit_pending` (a valid, tested transition) but nothing here ever moves it
on to `deposit_paid` — that hop exists in the graph for a future payments
phase's webhook handler to call directly.
"""

import uuid
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.enums import (
    BOOKING_OCCUPYING_STATUS_VALUES,
    AnalyticsEventType,
    BookingLocationType,
    BookingStatus,
    NotificationType,
    QuoteStatus,
    is_valid_booking_transition,
)
from app.db.models.artist import ArtistAvailability, ArtistBlockedDate, ArtistProfile, ArtistService
from app.db.models.booking import Booking, BookingQuote, BookingStatusHistory
from app.services.analytics.events import record_event
from app.services.notifications import notify_user
from app.services.scheduling import (
    effective_buffer_minutes,
    effective_travel_buffer_minutes,
    stored_weekday,
)

DRAFT_EDITABLE_FIELDS: tuple[str, ...] = (
    "service_id",
    "design_id",
    "requested_date",
    "requested_time",
    "location_type",
    "location_address",
    "event_type",
    "num_customers",
    "design_preferences",
    "notes",
    "budget_min",
    "budget_max",
    "contact_name",
    "contact_email",
    "contact_phone",
)

REQUIRED_SUBMISSION_FIELDS: tuple[str, ...] = (
    "service_id",
    "requested_date",
    "location_type",
    "contact_name",
    "contact_email",
    "contact_phone",
)

_RESCHEDULABLE_STATUSES = frozenset(
    {
        BookingStatus.REQUESTED.value,
        BookingStatus.ARTIST_REVIEWING.value,
        BookingStatus.QUOTATION_SENT.value,
        BookingStatus.CUSTOMER_REVIEWING.value,
        BookingStatus.CONFIRMED.value,
        BookingStatus.DEPOSIT_PENDING.value,
        BookingStatus.DEPOSIT_PAID.value,
    }
)

_QUOTABLE_STATUSES = frozenset(
    {
        BookingStatus.REQUESTED.value,
        BookingStatus.ARTIST_REVIEWING.value,
        BookingStatus.QUOTATION_SENT.value,
        BookingStatus.CUSTOMER_REVIEWING.value,
    }
)

_QUOTE_DECISION_STATUSES = frozenset(
    {BookingStatus.QUOTATION_SENT.value, BookingStatus.CUSTOMER_REVIEWING.value}
)


# --- Booking-status alerts ----------------------------------------------------
#
# See docs/booking-messaging.md#3b-booking-request-quote-and-status-alerts.
# Each higher-level action below sends its own bespoke, event-specific
# notification (a "quote alert" reads differently from a generic "status
# changed" notice) rather than a blanket auto-notify bolted onto
# `transition_booking()` — that would either double up with the specific
# notification or force every transition into one generic, less useful
# message.


def _artist_user_id(db: Session, artist_profile_id: uuid.UUID) -> uuid.UUID | None:
    return db.execute(
        select(ArtistProfile.user_id).where(ArtistProfile.id == artist_profile_id)
    ).scalar_one_or_none()


def _notify_other_party(
    db: Session, booking: Booking, *, exclude_user_id: uuid.UUID, title: str, body: str
) -> None:
    """Booking-status alert — notifies whichever party did *not* trigger the
    change (e.g. the artist cancels -> notify the customer)."""
    artist_user_id = _artist_user_id(db, booking.artist_profile_id)
    recipients = {booking.customer_id, artist_user_id} - {exclude_user_id, None}
    for recipient in recipients:
        assert recipient is not None
        notify_user(
            db,
            user_id=recipient,
            notification_type=NotificationType.BOOKING_UPDATE.value,
            title=title,
            body=body,
            data={"booking_id": str(booking.id)},
        )


# --- State-transition primitive ----------------------------------------------


def transition_booking(
    db: Session,
    booking: Booking,
    *,
    to_status: str,
    changed_by: uuid.UUID | None,
    reason: str | None = None,
) -> None:
    from_status = booking.status
    if not is_valid_booking_transition(BookingStatus(from_status), BookingStatus(to_status)):
        raise AppError(
            f"Cannot move a booking from '{from_status}' to '{to_status}'.", status_code=422
        )
    booking.status = to_status
    db.add(booking)
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
            reason=reason,
        )
    )


def record_history_note(
    db: Session, booking: Booking, *, changed_by: uuid.UUID | None, reason: str
) -> None:
    """Appends a same-status audit entry — used by actions like reschedule
    that don't change `booking.status` at all."""
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            from_status=booking.status,
            to_status=booking.status,
            changed_by=changed_by,
            reason=reason,
        )
    )


# --- Draft / submission -------------------------------------------------------


def create_draft_booking(
    db: Session, *, customer_id: uuid.UUID, artist_profile_id: uuid.UUID
) -> Booking:
    artist_profile = db.get(ArtistProfile, artist_profile_id)
    if artist_profile is None or artist_profile.deleted_at is not None:
        raise AppError("Artist not found.", status_code=404)
    if not artist_profile.is_accepting_bookings:
        raise AppError("This artist is not currently accepting bookings.", status_code=409)

    booking = Booking(
        customer_id=customer_id,
        artist_profile_id=artist_profile_id,
        status=BookingStatus.DRAFT.value,
    )
    db.add(booking)
    db.flush()
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            from_status=None,
            to_status=BookingStatus.DRAFT.value,
            changed_by=customer_id,
        )
    )
    db.flush()
    record_event(
        db,
        event_type=AnalyticsEventType.BOOKING_STARTED.value,
        user_id=customer_id,
        entity_type="booking",
        entity_id=booking.id,
    )
    return booking


def _validate_draft_fields(db: Session, booking: Booking, updates: dict[str, Any]) -> None:
    if "service_id" in updates and updates["service_id"] is not None:
        service = db.get(ArtistService, updates["service_id"])
        if (
            service is None
            or service.artist_profile_id != booking.artist_profile_id
            or service.deleted_at is not None
            or not service.is_active
        ):
            raise AppError("Service not found for this artist.", status_code=404)
    if "location_type" in updates and updates["location_type"] is not None:
        valid_location_types = {member.value for member in BookingLocationType}
        if updates["location_type"] not in valid_location_types:
            raise AppError(
                f"location_type must be one of: {', '.join(sorted(valid_location_types))}",
                status_code=422,
            )
    budget_min = updates.get("budget_min", booking.budget_min)
    budget_max = updates.get("budget_max", booking.budget_max)
    if budget_min is not None and budget_max is not None and budget_max < budget_min:
        raise AppError("budget_max must be greater than or equal to budget_min.", status_code=422)


def update_draft_booking(db: Session, booking: Booking, updates: dict[str, Any]) -> None:
    if booking.status != BookingStatus.DRAFT.value:
        raise AppError("Only a draft booking can be edited this way.", status_code=422)
    unknown = set(updates) - set(DRAFT_EDITABLE_FIELDS)
    if unknown:
        raise AppError(f"Unknown field(s): {', '.join(sorted(unknown))}", status_code=422)
    _validate_draft_fields(db, booking, updates)
    for field, value in updates.items():
        setattr(booking, field, value)
    db.add(booking)


def missing_submission_requirements(booking: Booking) -> list[str]:
    """Returns the empty list if `booking` is ready to submit."""
    missing = [f for f in REQUIRED_SUBMISSION_FIELDS if not getattr(booking, f)]
    address_required_location_types = (
        BookingLocationType.CUSTOMER_LOCATION.value,
        BookingLocationType.OTHER.value,
    )
    if (
        booking.location_type in address_required_location_types
        and not booking.location_address
        and "location_type" not in missing
    ):
        missing.append("location_address")
    return missing


def submit_booking(db: Session, booking: Booking, *, changed_by: uuid.UUID) -> None:
    missing = missing_submission_requirements(booking)
    if missing:
        raise AppError(
            f"Your booking request is missing required information: {', '.join(missing)}.",
            status_code=422,
        )
    transition_booking(
        db,
        booking,
        to_status=BookingStatus.REQUESTED.value,
        changed_by=changed_by,
        reason="Booking request submitted.",
    )
    record_event(
        db,
        event_type=AnalyticsEventType.BOOKING_SUBMITTED.value,
        user_id=booking.customer_id,
        entity_type="booking",
        entity_id=booking.id,
    )
    artist_user_id = _artist_user_id(db, booking.artist_profile_id)
    if artist_user_id is not None:
        notify_user(
            db,
            user_id=artist_user_id,
            notification_type=NotificationType.BOOKING_UPDATE.value,
            title="New booking request",
            body="You have a new booking request to review.",
            data={"booking_id": str(booking.id)},
        )


# --- Artist review / quotes ----------------------------------------------------


def start_artist_review(db: Session, booking: Booking, *, changed_by: uuid.UUID) -> None:
    transition_booking(
        db, booking, to_status=BookingStatus.ARTIST_REVIEWING.value, changed_by=changed_by
    )


def send_quote(
    db: Session,
    booking: Booking,
    *,
    amount: float,
    currency: str,
    terms: str | None,
    valid_until: datetime | None,
    changed_by: uuid.UUID,
) -> BookingQuote:
    """Creating a quote while none is pending is "quote creation"; creating
    one while the booking is already `quotation_sent`/`customer_reviewing`
    (an earlier quote still pending) is "quote revision" — the earlier quote
    is superseded and the booking's status does not change again."""
    if booking.status not in _QUOTABLE_STATUSES:
        raise AppError(
            f"Cannot send a quote while the booking is '{booking.status}'.", status_code=422
        )

    is_revision = booking.status in _QUOTE_DECISION_STATUSES
    pending = (
        db.execute(
            select(BookingQuote).where(
                BookingQuote.booking_id == booking.id,
                BookingQuote.status == QuoteStatus.PENDING.value,
            )
        )
        .scalars()
        .all()
    )
    for old_quote in pending:
        old_quote.status = QuoteStatus.SUPERSEDED.value
        db.add(old_quote)

    quote = BookingQuote(
        booking_id=booking.id,
        amount=amount,
        currency=currency,
        terms=terms,
        valid_until=valid_until,
        status=QuoteStatus.PENDING.value,
    )
    db.add(quote)
    db.flush()

    if is_revision:
        record_history_note(db, booking, changed_by=changed_by, reason="Quote revised.")
    else:
        transition_booking(
            db,
            booking,
            to_status=BookingStatus.QUOTATION_SENT.value,
            changed_by=changed_by,
            reason="Quote sent.",
        )
    notify_user(
        db,
        user_id=booking.customer_id,
        notification_type=NotificationType.BOOKING_UPDATE.value,
        title="You received a quote" if not is_revision else "Your quote was updated",
        body=f"The artist sent a quote of {currency} {amount}.",
        data={"booking_id": str(booking.id), "quote_id": str(quote.id)},
    )
    return quote


def start_customer_review(db: Session, booking: Booking, *, changed_by: uuid.UUID) -> None:
    transition_booking(
        db, booking, to_status=BookingStatus.CUSTOMER_REVIEWING.value, changed_by=changed_by
    )


def get_active_quote_or_404(db: Session, booking: Booking, quote_id: uuid.UUID) -> BookingQuote:
    quote = db.get(BookingQuote, quote_id)
    if quote is None or quote.booking_id != booking.id:
        raise AppError("Quote not found.", status_code=404)
    return quote


def reject_quote(
    db: Session, booking: Booking, quote: BookingQuote, *, changed_by: uuid.UUID, reason: str | None
) -> None:
    if booking.status not in _QUOTE_DECISION_STATUSES:
        raise AppError(
            f"Cannot reject a quote while the booking is '{booking.status}'.", status_code=422
        )
    if quote.status != QuoteStatus.PENDING.value:
        raise AppError("This quote is no longer pending.", status_code=409)

    quote.status = QuoteStatus.DECLINED.value
    db.add(quote)
    transition_booking(
        db, booking, to_status=BookingStatus.REJECTED.value, changed_by=changed_by, reason=reason
    )
    artist_user_id = _artist_user_id(db, booking.artist_profile_id)
    if artist_user_id is not None:
        notify_user(
            db,
            user_id=artist_user_id,
            notification_type=NotificationType.BOOKING_UPDATE.value,
            title="Quote declined",
            body="The customer declined your quote.",
            data={"booking_id": str(booking.id)},
        )


# --- Availability re-validation / overlap prevention --------------------------


def _duration_minutes(service: ArtistService | None) -> int:
    if service is not None and service.duration_minutes:
        return service.duration_minutes
    return 60  # no fixed-duration service on the booking — assume a 1-hour slot


def _booking_time_range_minutes(
    booking: Booking, service: ArtistService | None, artist_profile: ArtistProfile
) -> tuple[int, int]:
    """Whole-day occupancy (0, 1440) if no specific time was requested —
    treated the same as a whole-day blocked date."""
    if booking.requested_time is None:
        return 0, 24 * 60
    start = booking.requested_time.hour * 60 + booking.requested_time.minute
    gap = effective_buffer_minutes(artist_profile, service) if service is not None else 0
    travel_gap = (
        effective_travel_buffer_minutes(artist_profile, service) if service is not None else 0
    )
    end = start + _duration_minutes(service) + gap + travel_gap
    return start, min(end, 24 * 60)


def check_no_overlapping_confirmed_booking(
    db: Session, booking: Booking, service: ArtistService | None, artist_profile: ArtistProfile
) -> None:
    """See docs/booking-lifecycle.md#6-preventing-overlapping-confirmed-bookings.
    Only compares against other bookings that already occupy the calendar
    (BOOKING_OCCUPYING_STATUS_VALUES) — a merely-requested/quoted booking
    from a different customer for the same slot is not a conflict."""
    if booking.requested_date is None:
        raise AppError("This booking has no requested date.", status_code=422)

    candidates = (
        db.execute(
            select(Booking).where(
                Booking.artist_profile_id == booking.artist_profile_id,
                Booking.requested_date == booking.requested_date,
                Booking.status.in_(BOOKING_OCCUPYING_STATUS_VALUES),
                Booking.id != booking.id,
            )
        )
        .scalars()
        .all()
    )
    if not candidates:
        return

    new_start, new_end = _booking_time_range_minutes(booking, service, artist_profile)
    other_service_ids = [c.service_id for c in candidates if c.service_id is not None]
    other_services: dict[uuid.UUID, ArtistService] = {}
    if other_service_ids:
        rows = (
            db.execute(select(ArtistService).where(ArtistService.id.in_(other_service_ids)))
            .scalars()
            .all()
        )
        other_services = {s.id: s for s in rows}

    for other in candidates:
        other_service = other_services.get(other.service_id) if other.service_id else None
        other_start, other_end = _booking_time_range_minutes(other, other_service, artist_profile)
        if new_start < other_end and other_start < new_end:
            raise AppError(
                "This time is no longer available — it overlaps another confirmed booking.",
                status_code=409,
            )


def validate_availability_for_confirmation(
    db: Session, booking: Booking, service: ArtistService | None, artist_profile: ArtistProfile
) -> None:
    """Re-checks the requested date/time against the artist's current
    weekly rules and blocked dates — availability may have changed since the
    booking was first requested/quoted. See
    docs/booking-lifecycle.md#5-validating-availability-again-at-confirmation."""
    if booking.requested_date is None:
        raise AppError("This booking has no requested date.", status_code=422)

    blocks = (
        db.execute(
            select(ArtistBlockedDate).where(
                ArtistBlockedDate.artist_profile_id == booking.artist_profile_id,
                ArtistBlockedDate.start_date <= booking.requested_date,
                ArtistBlockedDate.end_date >= booking.requested_date,
            )
        )
        .scalars()
        .all()
    )
    for block in blocks:
        if block.start_time is None:
            raise AppError("The artist is not available on this date.", status_code=409)
        if booking.requested_time is not None and block.end_time is not None:
            if block.start_time <= booking.requested_time < block.end_time:
                raise AppError("The artist is not available at this time.", status_code=409)

    if booking.requested_time is None:
        return

    weekday = stored_weekday(booking.requested_date)
    req_start = booking.requested_time.hour * 60 + booking.requested_time.minute
    req_end = req_start + _duration_minutes(service)
    rules = (
        db.execute(
            select(ArtistAvailability).where(
                ArtistAvailability.artist_profile_id == booking.artist_profile_id,
                ArtistAvailability.day_of_week == weekday,
                ArtistAvailability.is_active.is_(True),
            )
        )
        .scalars()
        .all()
    )
    fits = any(
        (rule.start_time.hour * 60 + rule.start_time.minute) <= req_start
        and req_end <= (rule.end_time.hour * 60 + rule.end_time.minute)
        for rule in rules
    )
    if not fits:
        raise AppError("This time falls outside the artist's working hours.", status_code=409)


def _lock_artist_calendar(db: Session, artist_profile_id: uuid.UUID) -> ArtistProfile:
    """Locks the artist's profile row for the rest of this transaction so two
    concurrent confirmations for the same artist serialize rather than both
    passing the overlap check before either commits. Released automatically
    on commit/rollback (this codebase's session-per-request pattern)."""
    profile = db.execute(
        select(ArtistProfile).where(ArtistProfile.id == artist_profile_id).with_for_update()
    ).scalar_one_or_none()
    if profile is None:
        raise AppError("Artist not found.", status_code=404)
    return profile


def accept_quote(
    db: Session, booking: Booking, quote: BookingQuote, *, changed_by: uuid.UUID
) -> None:
    if booking.status not in _QUOTE_DECISION_STATUSES:
        raise AppError(
            f"Cannot accept a quote while the booking is '{booking.status}'.", status_code=422
        )
    if quote.status != QuoteStatus.PENDING.value:
        raise AppError("This quote is no longer pending.", status_code=409)
    if quote.valid_until is not None and quote.valid_until < datetime.now(UTC):
        raise AppError("This quote has expired.", status_code=409)

    # Locking the artist's row (not just re-running the overlap query) is
    # what actually prevents the race: without it, two concurrent accepts for
    # different bookings on the same artist/date could both read "no
    # conflict" before either has committed.
    artist_profile = _lock_artist_calendar(db, booking.artist_profile_id)
    service = db.get(ArtistService, booking.service_id) if booking.service_id else None

    validate_availability_for_confirmation(db, booking, service, artist_profile)
    check_no_overlapping_confirmed_booking(db, booking, service, artist_profile)

    target_status = (
        BookingStatus.DEPOSIT_PENDING.value
        if (service is not None and service.deposit_required)
        else BookingStatus.CONFIRMED.value
    )

    quote.status = QuoteStatus.ACCEPTED.value
    db.add(quote)
    booking.total_amount = quote.amount
    booking.currency = quote.currency
    if service is not None and service.deposit_required:
        booking.deposit_amount = service.deposit_amount
    db.add(booking)
    transition_booking(
        db, booking, to_status=target_status, changed_by=changed_by, reason="Quote accepted."
    )
    record_event(
        db,
        event_type=AnalyticsEventType.QUOTE_ACCEPTED.value,
        user_id=booking.customer_id,
        entity_type="booking",
        entity_id=booking.id,
        properties={"quote_amount": float(quote.amount)},
    )
    artist_user_id = _artist_user_id(db, booking.artist_profile_id)
    if artist_user_id is not None:
        notify_user(
            db,
            user_id=artist_user_id,
            notification_type=NotificationType.BOOKING_UPDATE.value,
            title="Booking confirmed",
            body=(
                "The customer accepted your quote — a deposit is now due."
                if target_status == BookingStatus.DEPOSIT_PENDING.value
                else "The customer accepted your quote and the booking is confirmed."
            ),
            data={"booking_id": str(booking.id)},
        )


# --- Cancellation / reschedule -------------------------------------------------


def cancel_booking(
    db: Session, booking: Booking, *, changed_by: uuid.UUID, reason: str | None
) -> None:
    transition_booking(
        db, booking, to_status=BookingStatus.CANCELLED.value, changed_by=changed_by, reason=reason
    )
    booking.cancelled_by = changed_by
    booking.cancellation_reason = reason
    booking.cancelled_at = datetime.now(UTC)
    db.add(booking)
    _notify_other_party(
        db,
        booking,
        exclude_user_id=changed_by,
        title="Booking cancelled",
        body="A booking was cancelled." + (f" Reason: {reason}" if reason else ""),
    )


def request_reschedule(
    db: Session,
    booking: Booking,
    *,
    new_date: date,
    new_time: time | None,
    changed_by: uuid.UUID,
    reason: str | None,
) -> None:
    if booking.status not in _RESCHEDULABLE_STATUSES:
        raise AppError(
            f"A booking in status '{booking.status}' cannot be rescheduled.", status_code=422
        )

    old_date, old_time = booking.requested_date, booking.requested_time
    is_occupying = booking.status in BOOKING_OCCUPYING_STATUS_VALUES

    artist_profile = (
        _lock_artist_calendar(db, booking.artist_profile_id)
        if is_occupying
        else db.get(ArtistProfile, booking.artist_profile_id)
    )
    if artist_profile is None:
        raise AppError("Artist not found.", status_code=404)
    service = db.get(ArtistService, booking.service_id) if booking.service_id else None

    booking.requested_date = new_date
    booking.requested_time = new_time

    if is_occupying:
        validate_availability_for_confirmation(db, booking, service, artist_profile)
        check_no_overlapping_confirmed_booking(db, booking, service, artist_profile)

    db.add(booking)
    note = reason or f"Rescheduled from {old_date} {old_time or ''} to {new_date} {new_time or ''}."
    record_history_note(db, booking, changed_by=changed_by, reason=note.strip())
    _notify_other_party(
        db,
        booking,
        exclude_user_id=changed_by,
        title="Booking rescheduled",
        body=f"The booking was rescheduled to {new_date}" + (f" {new_time}." if new_time else "."),
    )
