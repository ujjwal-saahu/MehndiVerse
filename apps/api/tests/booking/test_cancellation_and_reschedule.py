"""Booking cancellation and reschedule requests — see
docs/booking-lifecycle.md."""

from datetime import date, time

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_artist_profile,
    make_artist_service,
    make_availability_rule,
    make_booking,
    make_user,
)

_MONDAY = date(2026, 3, 9)


def test_customer_can_cancel_their_own_booking(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session, customer=customer, artist_profile=profile, status=BookingStatus.REQUESTED.value
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/cancel",
        json={"reason": "changed my mind"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["cancelled_by"] == str(customer.id)
    assert body["cancellation_reason"] == "changed my mind"
    assert body["cancelled_at"] is not None


def test_artist_can_also_cancel_a_booking(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    booking = make_booking(db_session, artist_profile=profile, status=BookingStatus.CONFIRMED.value)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        f"/api/v1/bookings/{booking.id}/cancel", json={}, headers=auth_headers(token)
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_third_party_cannot_cancel(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    third_party = make_user(db_session, role="customer")
    booking = make_booking(db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value)
    db_session.commit()
    token = sign_token(third_party.id, email=third_party.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/cancel", json={}, headers=auth_headers(token)
    )
    assert response.status_code == 403


def test_cancelling_an_already_cancelled_booking_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    booking = make_booking(db_session, artist_profile=profile, status=BookingStatus.CANCELLED.value)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        f"/api/v1/bookings/{booking.id}/cancel", json={}, headers=auth_headers(token)
    )
    assert response.status_code == 422


def test_reschedule_a_merely_requested_booking_skips_overlap_check(
    client: TestClient, db_session: Session
) -> None:
    """A `requested` booking doesn't occupy the calendar, so rescheduling it
    onto a date/time that another *confirmed* booking already holds is still
    allowed — it's still just a request."""
    profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    make_booking(
        db_session,
        artist_profile=profile,
        status=BookingStatus.CONFIRMED.value,
        service_id=service.id,
        requested_date=_MONDAY,
        requested_time=time(10, 0),
    )
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.REQUESTED.value,
        requested_date=date(2026, 3, 1),
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/reschedule",
        json={"new_date": str(_MONDAY), "new_time": "10:00:00", "reason": "prefer this day"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requested_date"] == str(_MONDAY)
    assert body["status"] == "requested"
    assert body["status_history"][-1]["from_status"] == body["status_history"][-1]["to_status"]


def test_reschedule_a_confirmed_booking_onto_an_overlapping_slot_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=1,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    make_booking(
        db_session,
        artist_profile=profile,
        status=BookingStatus.CONFIRMED.value,
        service_id=service.id,
        requested_date=_MONDAY,
        requested_time=time(10, 0),
    )
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.CONFIRMED.value,
        service_id=service.id,
        requested_date=date(2026, 3, 2),
        requested_time=time(9, 0),
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/reschedule",
        json={"new_date": str(_MONDAY), "new_time": "10:00:00"},
        headers=auth_headers(token),
    )
    assert response.status_code == 409


def test_reschedule_unknown_time_slot_requires_valid_hours(
    client: TestClient, db_session: Session
) -> None:
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
        status=BookingStatus.CONFIRMED.value,
        requested_date=date(2026, 3, 2),
        requested_time=time(9, 0),
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/reschedule",
        json={"new_date": str(_MONDAY), "new_time": "20:00:00"},
        headers=auth_headers(token),
    )
    assert response.status_code == 409
