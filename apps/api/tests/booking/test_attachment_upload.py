"""POST /bookings/{id}/attachments — see app/api/routes/bookings.py
::upload_booking_inspiration_image. Uncovered before Phase 26 (coverage
audit)."""

import io
import uuid

import httpx
import respx
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.booking import BookingAttachment
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_booking, make_user


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), color=(10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_upload_requires_authentication(client: TestClient, db_session: Session) -> None:
    booking = make_booking(db_session)
    db_session.commit()

    response = client.post(
        f"/api/v1/bookings/{booking.id}/attachments",
        files={"file": ("photo.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == 401


def test_owner_can_upload_an_attachment(
    client: TestClient, db_session: Session, storage_mock: respx.MockRouter
) -> None:
    customer = make_user(db_session)
    booking = make_booking(db_session, customer=customer)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    storage_mock.post(url__regex=r"/object/portfolio/.*").mock(
        return_value=httpx.Response(200, json={"Key": "portfolio/mock"})
    )

    response = client.post(
        f"/api/v1/bookings/{booking.id}/attachments",
        files={"file": ("photo.png", _png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()["attachment"]
    assert body["file_type"] == "image"
    assert body["file_url"]

    stored = db_session.execute(
        select(BookingAttachment).where(BookingAttachment.booking_id == booking.id)
    ).scalar_one()
    assert stored.uploaded_by == customer.id


def test_non_owner_cannot_upload_an_attachment(client: TestClient, db_session: Session) -> None:
    booking = make_booking(db_session)
    stranger = make_user(db_session)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/attachments",
        files={"file": ("photo.png", _png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_artist_party_cannot_upload_an_attachment(client: TestClient, db_session: Session) -> None:
    """Only the customer uploads inspiration images — the artist side of
    the booking is a different party under `_require_customer_owner`."""
    artist_profile = make_artist_profile(db_session)
    booking = make_booking(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="artist@example.com")

    response = client.post(
        f"/api/v1/bookings/{booking.id}/attachments",
        files={"file": ("photo.png", _png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_upload_returns_404_for_a_nonexistent_booking(
    client: TestClient, db_session: Session
) -> None:
    customer = make_user(db_session)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{uuid.uuid4()}/attachments",
        files={"file": ("photo.png", _png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_upload_rejects_an_invalid_image(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session)
    booking = make_booking(db_session, customer=customer)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/attachments",
        files={"file": ("not-an-image.png", b"not a real image", "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_upload_surfaces_a_storage_failure(
    client: TestClient, db_session: Session, storage_mock: respx.MockRouter
) -> None:
    customer = make_user(db_session)
    booking = make_booking(db_session, customer=customer)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    storage_mock.post(url__regex=r"/object/portfolio/.*").mock(
        return_value=httpx.Response(500, json={"message": "Storage unavailable"})
    )

    response = client.post(
        f"/api/v1/bookings/{booking.id}/attachments",
        files={"file": ("photo.png", _png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 502
