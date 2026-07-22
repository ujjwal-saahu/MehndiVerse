"""Artist review, quote creation/revision/accept/reject, and the
availability-revalidation + overlap-prevention that happens at confirmation
— see docs/booking-lifecycle.md."""

from datetime import UTC, date, datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from app.db.models.artist import ArtistProfile
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_artist_profile,
    make_artist_service,
    make_availability_rule,
    make_booking,
    make_booking_quote,
    make_user,
)

_MONDAY = date(2026, 3, 9)  # stored_weekday(_MONDAY) == 1, matches day_of_week=1 below


def _artist_with_monday_hours(db_session: Session) -> ArtistProfile:
    profile = make_artist_profile(db_session)
    make_availability_rule(
        db_session,
        artist_profile=profile,
        day_of_week=1,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    return profile


def test_start_review_transitions_requested_to_artist_reviewing(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    booking = make_booking(db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        f"/api/v1/artist/bookings/{booking.id}/review", headers=auth_headers(token)
    )
    assert response.status_code == 200
    assert response.json()["status"] == "artist_reviewing"


def test_non_owner_artist_cannot_send_a_quote(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    other_profile = make_artist_profile(db_session)
    booking = make_booking(db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value)
    db_session.commit()
    other_token = sign_token(other_profile.user_id, email="other@example.com")

    response = client.post(
        f"/api/v1/artist/bookings/{booking.id}/quotes",
        json={"amount": 5000, "currency": "INR"},
        headers=auth_headers(other_token),
    )
    assert response.status_code == 403


def test_send_quote_transitions_to_quotation_sent(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    booking = make_booking(db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        f"/api/v1/artist/bookings/{booking.id}/quotes",
        json={"amount": 5000, "currency": "INR", "terms": "50% deposit"},
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "quotation_sent"
    assert len(body["quotes"]) == 1
    assert body["quotes"][0]["status"] == "pending"


def test_second_quote_is_a_revision_that_supersedes_the_first(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    booking = make_booking(db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    client.post(
        f"/api/v1/artist/bookings/{booking.id}/quotes",
        json={"amount": 5000, "currency": "INR"},
        headers=auth_headers(token),
    )
    response = client.post(
        f"/api/v1/artist/bookings/{booking.id}/quotes",
        json={"amount": 4000, "currency": "INR"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "quotation_sent"  # unchanged by the revision
    assert len(body["quotes"]) == 2
    pending = [q for q in body["quotes"] if q["status"] == "pending"]
    superseded = [q for q in body["quotes"] if q["status"] == "superseded"]
    assert len(pending) == 1 and pending[0]["amount"] == 4000
    assert len(superseded) == 1 and superseded[0]["amount"] == 5000


def test_reject_quote_rejects_the_booking(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.QUOTATION_SENT.value,
    )
    quote = make_booking_quote(db_session, booking=booking)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/quotes/{quote.id}/reject",
        json={"reason": "too expensive"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["quotes"][0]["status"] == "declined"


def test_accept_quote_without_deposit_confirms_the_booking(
    client: TestClient, db_session: Session
) -> None:
    profile = _artist_with_monday_hours(db_session)
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.QUOTATION_SENT.value,
        service_id=service.id,
        requested_date=_MONDAY,
        requested_time=time(10, 0),
    )
    quote = make_booking_quote(db_session, booking=booking, amount=6000)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/quotes/{quote.id}/accept", headers=auth_headers(token)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["total_amount"] == 6000
    assert body["quotes"][0]["status"] == "accepted"


def test_accept_quote_with_deposit_required_lands_on_deposit_pending(
    client: TestClient, db_session: Session
) -> None:
    profile = _artist_with_monday_hours(db_session)
    service = make_artist_service(
        db_session,
        artist_profile=profile,
        duration_minutes=60,
        deposit_required=True,
        deposit_amount=1000,
    )
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.QUOTATION_SENT.value,
        service_id=service.id,
        requested_date=_MONDAY,
        requested_time=time(10, 0),
    )
    quote = make_booking_quote(db_session, booking=booking)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/quotes/{quote.id}/accept", headers=auth_headers(token)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "deposit_pending"
    assert body["deposit_amount"] == 1000


def test_accept_expired_quote_is_rejected(client: TestClient, db_session: Session) -> None:
    profile = _artist_with_monday_hours(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.QUOTATION_SENT.value,
        requested_date=_MONDAY,
        requested_time=time(10, 0),
    )
    quote = make_booking_quote(
        db_session, booking=booking, valid_until=datetime.now(UTC) - timedelta(days=1)
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/quotes/{quote.id}/accept", headers=auth_headers(token)
    )
    assert response.status_code == 409


def test_accept_quote_outside_working_hours_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    """The artist's weekly rule only covers 09:00-17:00; a booking requested
    for 20:00 must fail re-validation at confirmation time even though the
    quote itself is perfectly valid."""
    profile = _artist_with_monday_hours(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.QUOTATION_SENT.value,
        requested_date=_MONDAY,
        requested_time=time(20, 0),
    )
    quote = make_booking_quote(db_session, booking=booking)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/quotes/{quote.id}/accept", headers=auth_headers(token)
    )
    assert response.status_code == 409
    assert "working hours" in response.json()["error"]["message"]


def test_accept_quote_overlapping_an_existing_confirmed_booking_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    profile = _artist_with_monday_hours(db_session)
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
        status=BookingStatus.QUOTATION_SENT.value,
        service_id=service.id,
        requested_date=_MONDAY,
        requested_time=time(10, 30),
    )
    quote = make_booking_quote(db_session, booking=booking)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/quotes/{quote.id}/accept", headers=auth_headers(token)
    )
    assert response.status_code == 409
    assert "overlap" in response.json()["error"]["message"]


def test_accept_quote_non_overlapping_same_day_succeeds(
    client: TestClient, db_session: Session
) -> None:
    profile = _artist_with_monday_hours(db_session)
    service = make_artist_service(db_session, artist_profile=profile, duration_minutes=60)
    make_booking(
        db_session,
        artist_profile=profile,
        status=BookingStatus.CONFIRMED.value,
        service_id=service.id,
        requested_date=_MONDAY,
        requested_time=time(9, 0),
    )
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.QUOTATION_SENT.value,
        service_id=service.id,
        requested_date=_MONDAY,
        requested_time=time(11, 0),
    )
    quote = make_booking_quote(db_session, booking=booking)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/quotes/{quote.id}/accept", headers=auth_headers(token)
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
