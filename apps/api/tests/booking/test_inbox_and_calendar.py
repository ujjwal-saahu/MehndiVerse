"""Artist booking inbox, customer booking history, artist booking calendar —
see docs/booking-lifecycle.md."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_booking, make_user


def test_inbox_requires_an_artist_profile(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="artist")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/artist/bookings", headers=auth_headers(token))
    assert response.status_code == 404


def test_inbox_excludes_drafts_and_other_artists_bookings(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    other_profile = make_artist_profile(db_session)
    make_booking(db_session, artist_profile=profile, status=BookingStatus.DRAFT.value)
    make_booking(db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value)
    make_booking(db_session, artist_profile=other_profile, status=BookingStatus.REQUESTED.value)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get("/api/v1/artist/bookings", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "requested"


def test_inbox_filters_by_status(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    make_booking(db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value)
    make_booking(db_session, artist_profile=profile, status=BookingStatus.QUOTATION_SENT.value)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get(
        "/api/v1/artist/bookings",
        params={"status_filter": "quotation_sent"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "quotation_sent"


def test_customer_booking_history_only_shows_own_bookings(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    other_customer = make_user(db_session, role="customer")
    make_booking(
        db_session, customer=customer, artist_profile=profile, status=BookingStatus.DRAFT.value
    )
    make_booking(
        db_session,
        customer=other_customer,
        artist_profile=profile,
        status=BookingStatus.DRAFT.value,
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get("/api/v1/bookings/mine", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["customer_id"] == str(customer.id)


def test_calendar_only_includes_occupying_bookings(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    day = date(2026, 3, 9)
    make_booking(
        db_session, artist_profile=profile, status=BookingStatus.REQUESTED.value, requested_date=day
    )
    make_booking(
        db_session, artist_profile=profile, status=BookingStatus.CONFIRMED.value, requested_date=day
    )
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get(
        "/api/v1/artist/bookings/calendar",
        params={"start_date": "2026-03-01", "end_date": "2026-03-31"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "confirmed"


def test_calendar_rejects_end_before_start(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get(
        "/api/v1/artist/bookings/calendar",
        params={"start_date": "2026-03-31", "end_date": "2026-03-01"},
        headers=auth_headers(token),
    )
    assert response.status_code == 422
