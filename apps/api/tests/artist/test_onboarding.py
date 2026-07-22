import io

import httpx
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_user

_ID_PROOF_BYTES = b"%PDF-1.4 fake id document"


def _mock_document_storage(storage_mock) -> None:
    storage_mock.post(url__regex=r"/object/sign/verification-documents/").mock(
        return_value=httpx.Response(
            200, json={"signedURL": "/object/sign/verification-documents/mock?token=abc"}
        )
    )
    storage_mock.post(url__regex=r"/object/verification-documents/").mock(
        return_value=httpx.Response(200, json={"Key": "verification-documents/mock"})
    )


def test_get_profile_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/artist/profile")
    assert response.status_code == 401


def test_get_profile_lazily_creates_a_draft_and_promotes_role(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/artist/profile", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["verification_status"] == "draft"
    assert body["is_editable"] is True
    assert "professional_name" in body["missing_requirements"]
    assert "identity_document" in body["missing_requirements"]

    db_session.refresh(user)
    assert user.role == "artist"


def test_get_profile_is_idempotent(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    first = client.get("/api/v1/artist/profile", headers=auth_headers(token))
    second = client.get("/api/v1/artist/profile", headers=auth_headers(token))

    assert first.json()["id"] == second.json()["id"]


def test_staff_cannot_create_an_artist_profile(client: TestClient, db_session: Session) -> None:
    staff = make_user(db_session, role="moderator")
    db_session.commit()
    token = sign_token(staff.id, email=staff.email)

    response = client.get("/api/v1/artist/profile", headers=auth_headers(token))

    assert response.status_code == 403


def test_update_profile_requires_an_existing_application(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.patch(
        "/api/v1/artist/profile",
        json={"professional_name": "Henna by Priya"},
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_update_profile_fields(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    client.get("/api/v1/artist/profile", headers=auth_headers(token))

    response = client.patch(
        "/api/v1/artist/profile",
        json={
            "professional_name": "Henna by Priya",
            "bio": "Ten years of bridal henna experience.",
            "years_experience": 10,
            "country": "in",
            "city": "Jaipur",
            "service_areas": ["Jaipur", " Udaipur ", ""],
            "languages": ["Hindi", "English"],
            "contact_email": "priya@example.com",
            "social_links": {"instagram": "https://instagram.com/hennabypriya"},
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["professional_name"] == "Henna by Priya"
    assert body["country"] == "IN"
    assert body["service_areas"] == ["Jaipur", "Udaipur"]
    assert body["social_links"] == {"instagram": "https://instagram.com/hennabypriya"}


def test_update_profile_rejects_unknown_social_platform(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    client.get("/api/v1/artist/profile", headers=auth_headers(token))

    response = client.patch(
        "/api/v1/artist/profile",
        json={"social_links": {"myspace": "https://myspace.com/whoever"}},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_update_profile_rejects_invalid_country(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    client.get("/api/v1/artist/profile", headers=auth_headers(token))

    response = client.patch(
        "/api/v1/artist/profile", json={"country": "India"}, headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_submit_rejects_incomplete_application(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    client.get("/api/v1/artist/profile", headers=auth_headers(token))

    response = client.post("/api/v1/artist/profile/submit", headers=auth_headers(token))

    assert response.status_code == 422


def test_submit_succeeds_once_complete(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    client.get("/api/v1/artist/profile", headers=auth_headers(token))
    client.patch(
        "/api/v1/artist/profile",
        json={
            "professional_name": "Henna by Priya",
            "bio": "Ten years of bridal henna experience.",
            "years_experience": 10,
            "country": "IN",
            "city": "Jaipur",
        },
        headers=auth_headers(token),
    )
    _mock_document_storage(storage_mock)
    client.post(
        "/api/v1/artist/documents",
        data={"document_type": "id_proof"},
        files={"file": ("id.pdf", _ID_PROOF_BYTES, "application/pdf")},
        headers=auth_headers(token),
    )

    response = client.post("/api/v1/artist/profile/submit", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["verification_status"] == "submitted"
    assert body["submitted_at"] is not None
    assert body["is_editable"] is False


def test_cannot_edit_while_submitted(client: TestClient, db_session: Session, storage_mock) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    client.get("/api/v1/artist/profile", headers=auth_headers(token))
    client.patch(
        "/api/v1/artist/profile",
        json={
            "professional_name": "Henna by Priya",
            "bio": "Bio",
            "years_experience": 5,
            "country": "IN",
            "city": "Jaipur",
        },
        headers=auth_headers(token),
    )
    _mock_document_storage(storage_mock)
    client.post(
        "/api/v1/artist/documents",
        data={"document_type": "id_proof"},
        files={"file": ("id.pdf", _ID_PROOF_BYTES, "application/pdf")},
        headers=auth_headers(token),
    )
    client.post("/api/v1/artist/profile/submit", headers=auth_headers(token))

    response = client.patch(
        "/api/v1/artist/profile",
        json={"bio": "New bio"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def _tiny_png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(200, 100, 50)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_upload_profile_image(client: TestClient, db_session: Session, storage_mock) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    client.get("/api/v1/artist/profile", headers=auth_headers(token))
    storage_mock.post(url__regex=r"/object/portfolio/").mock(
        return_value=httpx.Response(200, json={"Key": "portfolio/mock"})
    )

    response = client.post(
        "/api/v1/artist/profile/image",
        files={"file": ("photo.png", _tiny_png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert "/object/public/portfolio/" in body["image_url"]

    profile = client.get("/api/v1/artist/profile", headers=auth_headers(token)).json()
    assert profile["profile_image_url"] == body["image_url"]


def test_upload_cover_image(client: TestClient, db_session: Session, storage_mock) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    client.get("/api/v1/artist/profile", headers=auth_headers(token))
    storage_mock.post(url__regex=r"/object/portfolio/").mock(
        return_value=httpx.Response(200, json={"Key": "portfolio/mock"})
    )

    response = client.post(
        "/api/v1/artist/profile/cover-image",
        files={"file": ("cover.png", _tiny_png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    profile = client.get("/api/v1/artist/profile", headers=auth_headers(token)).json()
    assert profile["cover_image_url"] == response.json()["image_url"]


def test_upload_profile_image_requires_an_existing_application(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/artist/profile/image",
        files={"file": ("photo.png", _tiny_png_bytes(), "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_upload_profile_image_rejects_invalid_bytes(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    client.get("/api/v1/artist/profile", headers=auth_headers(token))

    response = client.post(
        "/api/v1/artist/profile/image",
        files={"file": ("photo.png", b"not an image", "image/png")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_submit_twice_rejected(client: TestClient, db_session: Session, storage_mock) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    client.get("/api/v1/artist/profile", headers=auth_headers(token))
    client.patch(
        "/api/v1/artist/profile",
        json={
            "professional_name": "Henna by Priya",
            "bio": "Bio",
            "years_experience": 5,
            "country": "IN",
            "city": "Jaipur",
        },
        headers=auth_headers(token),
    )
    _mock_document_storage(storage_mock)
    client.post(
        "/api/v1/artist/documents",
        data={"document_type": "id_proof"},
        files={"file": ("id.pdf", _ID_PROOF_BYTES, "application/pdf")},
        headers=auth_headers(token),
    )
    client.post("/api/v1/artist/profile/submit", headers=auth_headers(token))

    response = client.post("/api/v1/artist/profile/submit", headers=auth_headers(token))

    assert response.status_code == 422
