"""Notification fan-out — see docs/booking-messaging.md#3-notifications.

`notify_user()` is the single place any other service reaches to notify
someone. One "logical" event (e.g. "you received a quote") can produce
*multiple* `Notification` rows — one per channel — because `Notification`
is schema'd (Phase 2) as one row per channel, giving a genuine per-channel
delivery history rather than a single channel-agnostic event log. An
in-app row is always written (there is no way to opt out of in-app
notifications — only email/push have a `UserPreference` toggle); push/email
rows are only written (and only "dispatched" to the Phase 14 foundation
stub) when the recipient's preference for that channel is enabled and, for
push, they have at least one active device.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import BOOKING_OCCUPYING_STATUS_VALUES, NotificationChannel
from app.db.models.booking import Booking
from app.db.models.notification import Notification
from app.db.models.user import User, UserDevice, UserPreference
from app.integrations.email_notifications import render_email_body, send_notification_email
from app.integrations.push_notifications import send_push_notification


def _get_preference(db: Session, user_id: uuid.UUID) -> UserPreference | None:
    return db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    ).scalar_one_or_none()


def notify_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    notification_type: str,
    title: str,
    body: str,
    data: dict[str, object] | None = None,
) -> list[Notification]:
    """Creates (and, for push/email, dispatches to the foundation stub) the
    notification row(s) for one event. Does not commit — callers write this
    in the same transaction as the event that triggered it."""
    preference = _get_preference(db, user_id)
    created: list[Notification] = []

    in_app = Notification(
        user_id=user_id,
        type=notification_type,
        channel=NotificationChannel.IN_APP.value,
        title=title,
        body=body,
        data=data,
        sent_at=datetime.now(UTC),
    )
    db.add(in_app)
    created.append(in_app)

    if preference is None or preference.push_notifications:
        devices = (
            db.execute(
                select(UserDevice.device_token).where(
                    UserDevice.user_id == user_id, UserDevice.is_active.is_(True)
                )
            )
            .scalars()
            .all()
        )
        push = Notification(
            user_id=user_id,
            type=notification_type,
            channel=NotificationChannel.PUSH.value,
            title=title,
            body=body,
            data=data,
        )
        if send_push_notification(
            device_tokens=list(devices), title=title, body=body, user_id=user_id
        ):
            push.sent_at = datetime.now(UTC)
        db.add(push)
        created.append(push)

    if preference is None or preference.email_notifications:
        user = db.get(User, user_id)
        if user is not None:
            email = Notification(
                user_id=user_id,
                type=notification_type,
                channel=NotificationChannel.EMAIL.value,
                title=title,
                body=body,
                data=data,
            )
            html_body = render_email_body(greeting=body)
            if send_notification_email(to_email=user.email, subject=title, html_body=html_body):
                email.sent_at = datetime.now(UTC)
            db.add(email)
            created.append(email)

    return created


def send_booking_reminders(db: Session, *, within_hours: int = 24) -> int:
    """Reminder **foundation** — see docs/booking-messaging.md#3d-reminder-
    foundation. Finds occupying bookings whose `requested_date` falls within
    the next `within_hours` hours and notifies both parties. Not wired to any
    scheduler in this phase (no cron/task-queue infrastructure exists yet) —
    intended to be called by a future periodic job. Safe to call repeatedly:
    callers are responsible for not double-sending (e.g. a future scheduler
    would track "already reminded" bookings itself); this function always
    sends for every matching booking passed to it.
    """
    from app.db.models.artist import ArtistProfile  # local import avoids a cycle with booking.py

    now = datetime.now(UTC)
    cutoff_date = (now + timedelta(hours=within_hours)).date()
    bookings = (
        db.execute(
            select(Booking).where(
                Booking.status.in_(BOOKING_OCCUPYING_STATUS_VALUES),
                Booking.requested_date.is_not(None),
                Booking.requested_date >= now.date(),
                Booking.requested_date <= cutoff_date,
            )
        )
        .scalars()
        .all()
    )

    count = 0
    for booking in bookings:
        artist_profile = db.get(ArtistProfile, booking.artist_profile_id)
        if artist_profile is None:
            continue
        when = booking.requested_date.isoformat() if booking.requested_date else "soon"
        notify_user(
            db,
            user_id=booking.customer_id,
            notification_type="booking_update",
            title="Upcoming appointment reminder",
            body=f"Your booking on {when} is coming up.",
            data={"booking_id": str(booking.id)},
        )
        notify_user(
            db,
            user_id=artist_profile.user_id,
            notification_type="booking_update",
            title="Upcoming appointment reminder",
            body=f"Your booking on {when} is coming up.",
            data={"booking_id": str(booking.id)},
        )
        count += 1
    return count
