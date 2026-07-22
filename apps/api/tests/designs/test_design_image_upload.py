import io

import httpx
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_design, make_user
from tests.designs.conftest import mock_successful_storage_upload


def _png_bytes(size: tuple[int, int] = (64, 48)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(80, 20, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


def _authorize(client: TestClient, design_id: str, token: str) -> str:
    response = client.post(
        f"/api/v1/designs/{design_id}/images/authorize", headers=auth_headers(token)
    )
    assert response.status_code == 201
    return str(response.json()["image_id"])


def test_authorize_requires_authentication(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session)
    db_session.commit()

    response = client.post(f"/api/v1/designs/{design.id}/images/authorize")

    assert response.status_code == 401


def test_owner_can_authorize_an_image_upload(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="uploader@example.com")

    response = client.post(
        f"/api/v1/designs/{design.id}/images/authorize", headers=auth_headers(token)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["image_id"]
    assert body["max_file_size_bytes"] > 0
    assert "image/png" in body["allowed_content_types"]


def test_non_owner_cannot_authorize_an_image_upload(
    client: TestClient, db_session: Session
) -> None:
    owner_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=owner_profile)
    stranger = make_user(db_session)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.post(
        f"/api/v1/designs/{design.id}/images/authorize", headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_full_upload_pipeline_marks_image_ready_with_thumbnails(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="pipeline@example.com")
    mock_successful_storage_upload(storage_mock)

    image_id = _authorize(client, str(design.id), token)

    response = client.post(
        f"/api/v1/designs/{design.id}/images/{image_id}/upload",
        files={"file": ("design.png", _png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["image_url"] is not None
    assert body["thumbnail_small_url"] is not None
    assert body["thumbnail_medium_url"] is not None
    assert body["width"] == 64
    assert body["height"] == 48

    # original + small thumbnail + medium thumbnail
    assert storage_mock.calls.call_count == 3


def test_upload_requires_ownership(client: TestClient, db_session: Session) -> None:
    owner_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=owner_profile)
    db_session.commit()
    owner_token = sign_token(owner_profile.user_id, email="owner5@example.com")
    image_id = _authorize(client, str(design.id), owner_token)

    stranger = make_user(db_session)
    db_session.commit()
    stranger_token = sign_token(stranger.id, email=stranger.email)

    response = client.post(
        f"/api/v1/designs/{design.id}/images/{image_id}/upload",
        files={"file": ("design.png", _png_bytes(), "image/png")},
        headers=auth_headers(stranger_token),
    )

    assert response.status_code == 403


def test_upload_rejects_disallowed_content_type(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="badtype@example.com")
    image_id = _authorize(client, str(design.id), token)

    response = client.post(
        f"/api/v1/designs/{design.id}/images/{image_id}/upload",
        files={"file": ("design.pdf", b"%PDF-1.4", "application/pdf")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_upload_rejects_bytes_disguised_as_an_image(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="disguised@example.com")
    image_id = _authorize(client, str(design.id), token)

    response = client.post(
        f"/api/v1/designs/{design.id}/images/{image_id}/upload",
        files={"file": ("design.png", b"not actually a png", "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_upload_rejects_oversized_image(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="oversized@example.com")
    image_id = _authorize(client, str(design.id), token)
    oversized = b"\x00" * (10 * 1024 * 1024 + 1)

    response = client.post(
        f"/api/v1/designs/{design.id}/images/{image_id}/upload",
        files={"file": ("design.png", oversized, "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_uploading_to_an_already_uploaded_image_is_rejected(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="doubleupload@example.com")
    mock_successful_storage_upload(storage_mock)
    image_id = _authorize(client, str(design.id), token)

    client.post(
        f"/api/v1/designs/{design.id}/images/{image_id}/upload",
        files={"file": ("design.png", _png_bytes(), "image/png")},
        headers=auth_headers(token),
    )
    response = client.post(
        f"/api/v1/designs/{design.id}/images/{image_id}/upload",
        files={"file": ("design.png", _png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 409


def test_upload_to_unrelated_design_is_404(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design_a = make_design(db_session, artist_profile=artist_profile)
    design_b = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="crossdesign@example.com")
    image_id = _authorize(client, str(design_a.id), token)

    response = client.post(
        f"/api/v1/designs/{design_b.id}/images/{image_id}/upload",
        files={"file": ("design.png", _png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_image_is_marked_failed_when_storage_upload_fails(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="storagefail@example.com")
    storage_mock.post(url__regex=r"/object/portfolio/.*").mock(
        return_value=httpx.Response(500, json={"message": "Storage unavailable"})
    )
    image_id = _authorize(client, str(design.id), token)

    response = client.post(
        f"/api/v1/designs/{design.id}/images/{image_id}/upload",
        files={"file": ("design.png", _png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["processing_error"]
    assert body["image_url"] is None
