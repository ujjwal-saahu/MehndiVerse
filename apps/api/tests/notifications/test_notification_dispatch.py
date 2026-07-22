"""app/services/notifications.py::notify_user and send_booking_reminders —
see docs/booking-messaging.md#3."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from app.db.models.notification import Notification
from app.services.notifications import notify_user, send_booking_reminders
from tests.db.factories import (
    make_artist_profile,
    make_booking,
    make_user,
    make_user_device,
    make_user_preference,
)


def test_notify_user_always_creates_an_in_app_row(db_session: Session) -> None:
    user = make_user(db_session)
    db_session.commit()

    notify_user(
        db_session, user_id=user.id, notification_type="system", title="Hi", body="Hello there"
    )
    db_session.commit()

    rows = (
        db_session.execute(select(Notification).where(Notification.user_id == user.id))
        .scalars()
        .all()
    )
    channels = {r.channel for r in rows}
    assert "in_app" in channels


def test_notify_user_skips_email_and_push_when_disabled(db_session: Session) -> None:
    user = make_user(db_session)
    make_user_preference(db_session, user=user, email_notifications=False, push_notifications=False)
    db_session.commit()

    notify_user(
        db_session, user_id=user.id, notification_type="system", title="Hi", body="Hello there"
    )
    db_session.commit()

    rows = (
        db_session.execute(select(Notification).where(Notification.user_id == user.id))
        .scalars()
        .all()
    )
    channels = {r.channel for r in rows}
    assert channels == {"in_app"}


def test_notify_user_sends_push_and_email_when_enabled(db_session: Session) -> None:
    user = make_user(db_session)
    make_user_preference(db_session, user=user, email_notifications=True, push_notifications=True)
    make_user_device(db_session, user=user)
    db_session.commit()

    notify_user(
        db_session, user_id=user.id, notification_type="system", title="Hi", body="Hello there"
    )
    db_session.commit()

    rows = (
        db_session.execute(select(Notification).where(Notification.user_id == user.id))
        .scalars()
        .all()
    )
    channels = {r.channel for r in rows}
    assert channels == {"in_app", "push", "email"}
    push_row = next(r for r in rows if r.channel == "push")
    email_row = next(r for r in rows if r.channel == "email")
    assert push_row.sent_at is not None
    assert email_row.sent_at is not None


def test_notify_user_push_row_unsent_without_a_registered_device(db_session: Session) -> None:
    user = make_user(db_session)
    make_user_preference(db_session, user=user, push_notifications=True)
    db_session.commit()

    notify_user(
        db_session, user_id=user.id, notification_type="system", title="Hi", body="Hello there"
    )
    db_session.commit()

    push_row = db_session.execute(
        select(Notification).where(Notification.user_id == user.id, Notification.channel == "push")
    ).scalar_one()
    assert push_row.sent_at is None


def test_send_booking_reminders_notifies_both_parties_for_upcoming_bookings(
    db_session: Session,
) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    upcoming = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.CONFIRMED.value,
        requested_date=date.today(),
    )
    far_future = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.CONFIRMED.value,
        requested_date=date.today() + timedelta(days=30),
    )
    db_session.commit()

    count = send_booking_reminders(db_session, within_hours=24)
    db_session.commit()

    assert count == 1
    customer_notifications = (
        db_session.execute(select(Notification).where(Notification.user_id == customer.id))
        .scalars()
        .all()
    )
    assert any(
        n.data and n.data.get("booking_id") == str(upcoming.id) for n in customer_notifications
    )
    assert not any(
        n.data and n.data.get("booking_id") == str(far_future.id) for n in customer_notifications
    )
