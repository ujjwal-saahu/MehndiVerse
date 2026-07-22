"""Conversation list — see docs/booking-messaging.md#1. Booking context and
unread counts, and that private contact fields never leak into this
response (see docs/booking-messaging.md#6)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_artist_service, make_booking, make_user


def test_conversation_list_shows_booking_context_without_contact_info(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=profile, name="Bridal Henna")
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.REQUESTED.value,
        service_id=service.id,
    )
    db_session.commit()
    customer_token = sign_token(customer.id, email=customer.email)

    client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        data={"body": "hi there"},
        headers=auth_headers(customer_token),
    )

    response = client.get("/api/v1/conversations", headers=auth_headers(customer_token))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    conversation = body[0]
    assert conversation["booking"]["service_name"] == "Bridal Henna"
    assert conversation["booking"]["status"] == "requested"
    assert conversation["last_message_preview"] == "hi there"
    assert "contact_email" not in conversation
    assert "contact_phone" not in conversation
    assert "contact_email" not in conversation["booking"]
    assert "contact_phone" not in conversation["booking"]


def test_conversation_list_unread_count(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session, customer=customer, artist_profile=profile, status=BookingStatus.REQUESTED.value
    )
    db_session.commit()
    customer_token = sign_token(customer.id, email=customer.email)
    artist_token = sign_token(profile.user_id, email="artist@example.com")

    client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        data={"body": "one"},
        headers=auth_headers(customer_token),
    )
    client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        data={"body": "two"},
        headers=auth_headers(customer_token),
    )

    artist_view = client.get("/api/v1/conversations", headers=auth_headers(artist_token)).json()
    assert artist_view[0]["unread_count"] == 2

    client.post(
        f"/api/v1/bookings/{booking.id}/conversation/read", headers=auth_headers(artist_token)
    )

    artist_view_after_read = client.get(
        "/api/v1/conversations", headers=auth_headers(artist_token)
    ).json()
    assert artist_view_after_read[0]["unread_count"] == 0


def test_conversation_list_only_includes_my_own_conversations(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    other_profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    other_customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session, customer=customer, artist_profile=profile, status=BookingStatus.REQUESTED.value
    )
    other_booking = make_booking(
        db_session,
        customer=other_customer,
        artist_profile=other_profile,
        status=BookingStatus.REQUESTED.value,
    )
    db_session.commit()
    customer_token = sign_token(customer.id, email=customer.email)
    other_token = sign_token(other_customer.id, email=other_customer.email)

    client.get(f"/api/v1/bookings/{booking.id}/conversation", headers=auth_headers(customer_token))
    client.get(
        f"/api/v1/bookings/{other_booking.id}/conversation", headers=auth_headers(other_token)
    )

    response = client.get("/api/v1/conversations", headers=auth_headers(customer_token))
    body = response.json()
    assert len(body) == 1
    assert body[0]["booking"]["booking_id"] == str(booking.id)
