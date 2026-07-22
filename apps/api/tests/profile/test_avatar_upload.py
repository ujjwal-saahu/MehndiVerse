import io

import httpx
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import get_settings
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_user


def _png_bytes(size: tuple[int, int] = (32, 32)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(120, 40, 60)).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_bytes_with_exif() -> bytes:
    image = Image.new("RGB", (32, 32), color=(200, 150, 20))
    exif = Image.Exif()
    exif[0x9003] = "2024:01:01 12:00:00"  # DateTimeOriginal
    exif[0x010F] = "PhoneCameraMaker"  # Make — stands in for device-identifying metadata
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    return buffer.getvalue()


def _mock_upload(storage_mock, *, status_code: int = 200) -> None:
    storage_mock.post(url__regex=r"/object/avatars/.*").mock(
        return_value=httpx.Response(status_code, json={"Key": "avatars/mock"})
    )


def test_avatar_upload_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/users/me/avatar", files={"file": ("avatar.png", _png_bytes(), "image/png")}
    )
    assert response.status_code == 401


def test_valid_png_upload_succeeds(client: TestClient, db_session: Session, storage_mock) -> None:
    user = make_user(db_session, email="avatar-ok@example.com")
    token = sign_token(user.id, email=user.email)
    _mock_upload(storage_mock)

    response = client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("avatar.png", _png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    settings = get_settings()
    assert response.json()["avatar_url"].startswith(
        f"{settings.supabase_url}/storage/v1/object/public/avatars/{user.id}/"
    )

    profile_response = client.get("/api/v1/users/me/profile", headers=auth_headers(token))
    assert profile_response.json()["avatar_url"] == response.json()["avatar_url"]


def test_disallowed_content_type_is_rejected(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, email="avatar-badtype@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("doc.pdf", b"%PDF-1.4 not really a pdf", "application/pdf")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_non_image_bytes_disguised_as_png_are_rejected(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, email="avatar-disguised@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("fake.png", b"this is not actually a png file", "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_oversized_image_is_rejected(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, email="avatar-oversized@example.com")
    token = sign_token(user.id, email=user.email)
    oversized = b"\x00" * (5 * 1024 * 1024 + 1)

    response = client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("big.png", oversized, "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_exif_metadata_is_stripped_before_upload(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    user = make_user(db_session, email="avatar-exif@example.com")
    token = sign_token(user.id, email=user.email)

    captured: dict[str, bytes] = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        return httpx.Response(200, json={"Key": "avatars/mock"})

    storage_mock.post(url__regex=r"/object/avatars/.*").mock(side_effect=_capture)

    source = _jpeg_bytes_with_exif()
    assert Image.open(io.BytesIO(source)).getexif()  # sanity: source really has EXIF

    response = client.post(
        "/api/v1/users/me/avatar",
        files={"file": ("avatar.jpg", source, "image/jpeg")},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    uploaded_image = Image.open(io.BytesIO(captured["body"]))
    assert not uploaded_image.getexif()
