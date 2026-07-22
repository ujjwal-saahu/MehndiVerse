"""Sending/listing booking messages — text, image attachments, pagination,
read status, rate limiting, content sanitization, and blocked-user
prevention. See docs/booking-messaging.md."""

import io
from datetime import UTC, datetime, timedelta

import httpx
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from app.db.models.user import User
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_artist_profile,
    make_booking,
    make_conversation,
    make_message,
    make_user,
    make_user_block,
)


def _tiny_png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


def _setup_booking(db_session: Session):
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session, customer=customer, artist_profile=profile, status=BookingStatus.REQUESTED.value
    )
    db_session.commit()
    return profile, customer, booking


def test_send_text_message(client: TestClient, db_session: Session) -> None:
    profile, customer, booking = _setup_booking(db_session)
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        data={"body": "Hello, when are you free?"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["body"] == "Hello, when are you free?"
    assert body["message_type"] == "text"
    assert body["attachment_url"] is None
    assert body["is_read"] is False


def test_message_requires_body_or_attachment(client: TestClient, db_session: Session) -> None:
    profile, customer, booking = _setup_booking(db_session)
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        data={},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_message_body_strips_html_tags(client: TestClient, db_session: Session) -> None:
    profile, customer, booking = _setup_booking(db_session)
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        data={"body": "<script>alert(1)</script>Hello <b>there</b>"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["body"] == "alert(1)Hello there"


def test_send_image_message(client: TestClient, db_session: Session, storage_mock) -> None:
    profile, customer, booking = _setup_booking(db_session)
    token = sign_token(customer.id, email=customer.email)
    storage_mock.post(url__regex=r"/object/portfolio/").mock(
        return_value=httpx.Response(200, json={"Key": "portfolio/mock"})
    )

    response = client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        data={"body": "check this out"},
        files={"file": ("design.png", _tiny_png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message_type"] == "image"
    assert "/object/public/portfolio/" in body["attachment_url"]


def test_invalid_image_attachment_is_rejected(client: TestClient, db_session: Session) -> None:
    profile, customer, booking = _setup_booking(db_session)
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        files={"file": ("not-an-image.png", b"not actually an image", "image/png")},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_blocked_user_cannot_message(client: TestClient, db_session: Session) -> None:
    profile, customer, booking = _setup_booking(db_session)
    artist_user = db_session.get(User, profile.user_id)
    assert artist_user is not None
    make_user_block(db_session, blocker=customer, blocked=artist_user)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        data={"body": "hello?"},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_message_pagination(client: TestClient, db_session: Session) -> None:
    """Seeds 35 messages directly (rather than via 35 HTTP sends, which
    would trip the message rate limit within a single test — see
    test_message_rate_limiting below for that behavior) with strictly
    increasing timestamps, so cursor ordering is deterministic."""
    profile, customer, booking = _setup_booking(db_session)
    token = sign_token(customer.id, email=customer.email)
    conversation = make_conversation(db_session, booking=booking)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(35):
        make_message(
            db_session,
            conversation=conversation,
            sender=customer,
            body=f"message {i}",
            created_at=base + timedelta(seconds=i),
        )
    db_session.commit()

    first_page = client.get(
        f"/api/v1/bookings/{booking.id}/conversation/messages", headers=auth_headers(token)
    ).json()
    assert len(first_page["items"]) == 30
    assert first_page["page_info"]["has_more"] is True
    # Newest first.
    assert first_page["items"][0]["body"] == "message 34"

    second_page = client.get(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        params={"cursor": first_page["page_info"]["next_cursor"]},
        headers=auth_headers(token),
    ).json()
    assert len(second_page["items"]) == 5
    assert second_page["page_info"]["has_more"] is False
    assert second_page["items"][-1]["body"] == "message 0"


def test_read_status_reflects_the_recipient_not_the_viewer(
    client: TestClient, db_session: Session
) -> None:
    profile, customer, booking = _setup_booking(db_session)
    customer_token = sign_token(customer.id, email=customer.email)
    artist_token = sign_token(profile.user_id, email="artist@example.com")

    client.post(
        f"/api/v1/bookings/{booking.id}/conversation/messages",
        data={"body": "from customer"},
        headers=auth_headers(customer_token),
    )
    # Not yet read by the artist.
    unread_view = client.get(
        f"/api/v1/bookings/{booking.id}/conversation/messages", headers=auth_headers(customer_token)
    ).json()
    assert unread_view["items"][0]["is_read"] is False

    client.post(
        f"/api/v1/bookings/{booking.id}/conversation/read", headers=auth_headers(artist_token)
    )

    read_view = client.get(
        f"/api/v1/bookings/{booking.id}/conversation/messages", headers=auth_headers(customer_token)
    ).json()
    assert read_view["items"][0]["is_read"] is True


def test_message_rate_limiting(client: TestClient, db_session: Session) -> None:
    profile, customer, booking = _setup_booking(db_session)
    token = sign_token(customer.id, email=customer.email)

    statuses = [
        client.post(
            f"/api/v1/bookings/{booking.id}/conversation/messages",
            data={"body": f"msg {i}"},
            headers=auth_headers(token),
        ).status_code
        for i in range(21)
    ]

    assert statuses[:20] == [201] * 20
    assert statuses[20] == 429
