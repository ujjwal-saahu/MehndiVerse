"""Booking-request/quote/status alerts — see
docs/booking-messaging.md#3b. Verifies the notification side-effects wired
into app/services/booking.py's actions, not the booking transitions
themselves (already covered by tests/booking/test_quotes_and_confirmation.py
etc.)."""

import uuid
from datetime import date, time

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from app.db.models.notification import Notification
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_artist_profile,
    make_artist_service,
    make_availability_rule,
    make_booking,
    make_booking_quote,
    make_user,
)


def _notification_titles(db_session: Session, user_id: uuid.UUID) -> list[str]:
    rows = (
        db_session.execute(
            select(Notification).where(
                Notification.user_id == user_id, Notification.channel == "in_app"
            )
        )
        .scalars()
        .all()
    )
    return [r.title for r in rows]


def test_submitting_a_booking_notifies_the_artist(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=profile)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    created = client.post(
        "/api/v1/bookings", json={"artist_profile_id": str(profile.id)}, headers=auth_headers(token)
    ).json()
    client.patch(
        f"/api/v1/bookings/{created['id']}",
        json={
            "service_id": str(service.id),
            "requested_date": "2026-03-09",
            "location_type": "artist_studio",
            "contact_name": "Test",
            "contact_email": "test@example.com",
            "contact_phone": "+911234567890",
        },
        headers=auth_headers(token),
    )
    client.post(f"/api/v1/bookings/{created['id']}/submit", headers=auth_headers(token))

    assert "New booking request" in _notification_titles(db_session, profile.user_id)


def test_sending_a_quote_notifies_the_customer(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session, customer=customer, artist_profile=profile, status=BookingStatus.REQUESTED.value
    )
    db_session.commit()
    artist_token = sign_token(profile.user_id, email="artist@example.com")

    client.post(
        f"/api/v1/artist/bookings/{booking.id}/quotes",
        json={"amount": 5000, "currency": "INR"},
        headers=auth_headers(artist_token),
    )

    assert "You received a quote" in _notification_titles(db_session, customer.id)


def test_accepting_a_quote_notifies_the_artist(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=1,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.QUOTATION_SENT.value,
        requested_date=date(2026, 3, 9),
        requested_time=time(10, 0),
    )
    quote = make_booking_quote(db_session, booking=booking)
    db_session.commit()
    customer_token = sign_token(customer.id, email=customer.email)

    client.post(
        f"/api/v1/bookings/{booking.id}/quotes/{quote.id}/accept",
        headers=auth_headers(customer_token),
    )

    assert "Booking confirmed" in _notification_titles(db_session, profile.user_id)


def test_cancelling_notifies_the_other_party(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session, customer=customer, artist_profile=profile, status=BookingStatus.REQUESTED.value
    )
    db_session.commit()
    customer_token = sign_token(customer.id, email=customer.email)

    client.post(
        f"/api/v1/bookings/{booking.id}/cancel", json={}, headers=auth_headers(customer_token)
    )

    assert "Booking cancelled" in _notification_titles(db_session, profile.user_id)
    # The customer triggered the cancellation, so they shouldn't also
    # receive a "your booking was cancelled" notice about their own action.
    assert "Booking cancelled" not in _notification_titles(db_session, customer.id)
