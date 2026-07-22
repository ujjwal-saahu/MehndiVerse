import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_user


def _mock_document_storage(storage_mock) -> None:
    storage_mock.post(url__regex=r"/object/sign/verification-documents/").mock(
        return_value=httpx.Response(
            200, json={"signedURL": "/object/sign/verification-documents/mock?token=abc"}
        )
    )
    storage_mock.post(url__regex=r"/object/verification-documents/").mock(
        return_value=httpx.Response(200, json={"Key": "verification-documents/mock"})
    )


def _onboard(client: TestClient, token: str) -> None:
    client.get("/api/v1/artist/profile", headers=auth_headers(token))


def test_upload_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/artist/documents",
        data={"document_type": "id_proof"},
        files={"file": ("id.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 401


def test_upload_requires_an_existing_application(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/artist/documents",
        data={"document_type": "id_proof"},
        files={"file": ("id.pdf", b"%PDF-1.4", "application/pdf")},
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_upload_pdf_document(client: TestClient, db_session: Session, storage_mock) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    _onboard(client, token)
    _mock_document_storage(storage_mock)

    response = client.post(
        "/api/v1/artist/documents",
        data={"document_type": "id_proof"},
        files={"file": ("id.pdf", b"%PDF-1.4 fake id", "application/pdf")},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["document_type"] == "id_proof"
    assert body["status"] == "pending"
    assert body["content_type"] == "application/pdf"
    # A short-lived signed URL, never a durable/public one.
    assert "/object/sign/verification-documents/" in body["view_url"]
    assert "/object/public/" not in body["view_url"]


def test_upload_rejects_invalid_document_type(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    _onboard(client, token)

    response = client.post(
        "/api/v1/artist/documents",
        data={"document_type": "not_a_real_type"},
        files={"file": ("id.pdf", b"%PDF-1.4", "application/pdf")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_upload_rejects_non_pdf_non_image_bytes(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    _onboard(client, token)

    response = client.post(
        "/api/v1/artist/documents",
        data={"document_type": "id_proof"},
        files={"file": ("id.txt", b"not a real document", "text/plain")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_upload_rejects_bytes_disguised_as_pdf(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    _onboard(client, token)

    response = client.post(
        "/api/v1/artist/documents",
        data={"document_type": "id_proof"},
        files={"file": ("id.pdf", b"this is not a pdf", "application/pdf")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_optional_business_document_type(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    _onboard(client, token)
    _mock_document_storage(storage_mock)

    response = client.post(
        "/api/v1/artist/documents",
        data={"document_type": "business_license"},
        files={"file": ("license.pdf", b"%PDF-1.4 license", "application/pdf")},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["document_type"] == "business_license"


def test_list_my_documents(client: TestClient, db_session: Session, storage_mock) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    _onboard(client, token)
    _mock_document_storage(storage_mock)
    client.post(
        "/api/v1/artist/documents",
        data={"document_type": "id_proof"},
        files={"file": ("id.pdf", b"%PDF-1.4 id", "application/pdf")},
        headers=auth_headers(token),
    )

    response = client.get("/api/v1/artist/documents", headers=auth_headers(token))

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_cannot_upload_once_submitted(
    client: TestClient, db_session: Session, storage_mock
) -> None:
    user = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    _onboard(client, token)
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
        files={"file": ("id.pdf", b"%PDF-1.4 id", "application/pdf")},
        headers=auth_headers(token),
    )
    client.post("/api/v1/artist/profile/submit", headers=auth_headers(token))

    response = client.post(
        "/api/v1/artist/documents",
        data={"document_type": "id_proof"},
        files={"file": ("id2.pdf", b"%PDF-1.4 id2", "application/pdf")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
