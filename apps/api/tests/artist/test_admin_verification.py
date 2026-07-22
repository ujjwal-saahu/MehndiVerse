import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.artist import ArtistDocument
from app.db.models.system import AuditLog
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_user


def _submitted_artist(db_session: Session):
    artist_profile = make_artist_profile(db_session)
    artist_profile.verification_status = "submitted"
    db_session.add(artist_profile)
    db_session.commit()
    return artist_profile


def _under_review_artist(db_session: Session):
    artist_profile = make_artist_profile(db_session)
    artist_profile.verification_status = "under_review"
    db_session.add(artist_profile)
    db_session.commit()
    return artist_profile


def _approved_artist(db_session: Session):
    artist_profile = make_artist_profile(db_session)
    artist_profile.verification_status = "approved"
    db_session.add(artist_profile)
    db_session.commit()
    return artist_profile


def test_queue_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/admin/artists")
    assert response.status_code == 401


def test_queue_requires_staff_role(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get("/api/v1/admin/artists", headers=auth_headers(token))

    assert response.status_code == 403


def test_moderator_can_view_queue(client: TestClient, db_session: Session) -> None:
    _submitted_artist(db_session)
    moderator = make_user(db_session, role="moderator")
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get("/api/v1/admin/artists", headers=auth_headers(token))

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_queue_defaults_to_submitted_and_under_review(
    client: TestClient, db_session: Session
) -> None:
    submitted = _submitted_artist(db_session)
    under_review = _under_review_artist(db_session)
    _approved_artist(db_session)
    moderator = make_user(db_session, role="moderator")
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get("/api/v1/admin/artists", headers=auth_headers(token))

    ids = {item["id"] for item in response.json()["items"]}
    assert ids == {str(submitted.id), str(under_review.id)}


def test_moderator_cannot_start_review(client: TestClient, db_session: Session) -> None:
    artist_profile = _submitted_artist(db_session)
    moderator = make_user(db_session, role="moderator")
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.post(
        f"/api/v1/admin/artists/{artist_profile.id}/start-review", headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_admin_can_start_review(client: TestClient, db_session: Session) -> None:
    artist_profile = _submitted_artist(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/artists/{artist_profile.id}/start-review", headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["verification_status"] == "under_review"


def test_admin_cannot_approve_their_own_application(
    client: TestClient, db_session: Session
) -> None:
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    artist_profile = make_artist_profile(db_session, user=admin)
    artist_profile.verification_status = "under_review"
    db_session.add(artist_profile)
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/artists/{artist_profile.id}/approve", headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_approve_transitions_to_approved(client: TestClient, db_session: Session) -> None:
    artist_profile = _under_review_artist(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/artists/{artist_profile.id}/approve", headers=auth_headers(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verification_status"] == "approved"
    assert body["reviewed_at"] is not None


def test_cannot_approve_directly_from_submitted(client: TestClient, db_session: Session) -> None:
    artist_profile = _submitted_artist(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/artists/{artist_profile.id}/approve", headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_reject_requires_a_reason(client: TestClient, db_session: Session) -> None:
    artist_profile = _under_review_artist(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/artists/{artist_profile.id}/reject",
        json={"reason": ""},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_reject_with_reason(client: TestClient, db_session: Session) -> None:
    artist_profile = _under_review_artist(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/artists/{artist_profile.id}/reject",
        json={"reason": "ID document is unreadable."},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verification_status"] == "rejected"
    assert body["rejection_reason"] == "ID document is unreadable."


def test_request_more_information(client: TestClient, db_session: Session) -> None:
    artist_profile = _under_review_artist(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/artists/{artist_profile.id}/request-more-information",
        json={"message": "Please upload a clearer photo of your ID."},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verification_status"] == "more_information_required"
    assert body["more_info_request"] == "Please upload a clearer photo of your ID."


def test_suspend_an_approved_artist(client: TestClient, db_session: Session) -> None:
    artist_profile = _approved_artist(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/artists/{artist_profile.id}/suspend",
        json={"reason": "Repeated customer complaints."},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["verification_status"] == "suspended"


def test_reinstate_a_suspended_artist(client: TestClient, db_session: Session) -> None:
    artist_profile = _approved_artist(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)
    client.post(
        f"/api/v1/admin/artists/{artist_profile.id}/suspend",
        json={"reason": "Policy violation."},
        headers=auth_headers(token),
    )

    response = client.post(
        f"/api/v1/admin/artists/{artist_profile.id}/approve", headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["verification_status"] == "approved"


def test_artist_can_resubmit_after_rejection(client: TestClient, db_session: Session) -> None:
    artist_profile = _under_review_artist(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    admin_token = sign_token(admin.id, email=admin.email)
    client.post(
        f"/api/v1/admin/artists/{artist_profile.id}/reject",
        json={"reason": "Missing info."},
        headers=auth_headers(admin_token),
    )
    artist_profile.professional_name = "Henna by Priya"
    artist_profile.bio = "Bio"
    artist_profile.years_experience = 5
    artist_profile.country = "IN"
    artist_profile.city = "Jaipur"
    db_session.add(artist_profile)
    db_session.commit()

    db_session.add(
        ArtistDocument(
            artist_profile_id=artist_profile.id,
            document_type="id_proof",
            storage_path=f"{artist_profile.user_id}/id.pdf",
            content_type="application/pdf",
            file_size_bytes=1024,
        )
    )
    db_session.commit()
    artist_token = sign_token(artist_profile.user_id, email="artist@example.com")

    response = client.post("/api/v1/artist/profile/submit", headers=auth_headers(artist_token))

    assert response.status_code == 200
    body = response.json()
    assert body["verification_status"] == "submitted"
    assert body["rejection_reason"] is None


def test_every_transition_writes_an_audit_log_entry(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = _under_review_artist(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    client.post(f"/api/v1/admin/artists/{artist_profile.id}/approve", headers=auth_headers(token))

    entries = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "artist_profiles", AuditLog.entity_id == artist_profile.id)
        .all()
    )
    assert len(entries) == 1
    assert entries[0].action == "artist_verification.approve"
    assert entries[0].actor_id == admin.id
    assert entries[0].before_state == {"verification_status": "under_review"}
    assert entries[0].after_state == {"verification_status": "approved"}


def test_audit_log_endpoint_returns_history(client: TestClient, db_session: Session) -> None:
    artist_profile = _under_review_artist(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)
    client.post(f"/api/v1/admin/artists/{artist_profile.id}/approve", headers=auth_headers(token))

    response = client.get(
        f"/api/v1/admin/artists/{artist_profile.id}/audit-log", headers=auth_headers(token)
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["action"] == "artist_verification.approve"


def test_document_review_approve(client: TestClient, db_session: Session, storage_mock) -> None:
    artist_profile = _under_review_artist(db_session)

    document = ArtistDocument(
        artist_profile_id=artist_profile.id,
        document_type="id_proof",
        storage_path=f"{artist_profile.user_id}/id.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
    )
    db_session.add(document)
    db_session.commit()
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)
    storage_mock.post(url__regex=r"/object/sign/verification-documents/").mock(
        return_value=httpx.Response(
            200, json={"signedURL": "/object/sign/verification-documents/mock?token=abc"}
        )
    )

    response = client.patch(
        f"/api/v1/admin/artists/{artist_profile.id}/documents/{document.id}",
        json={"status": "approved"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_document_review_reject_requires_reason(client: TestClient, db_session: Session) -> None:
    artist_profile = _under_review_artist(db_session)

    document = ArtistDocument(
        artist_profile_id=artist_profile.id,
        document_type="id_proof",
        storage_path=f"{artist_profile.user_id}/id.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
    )
    db_session.add(document)
    db_session.commit()
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.patch(
        f"/api/v1/admin/artists/{artist_profile.id}/documents/{document.id}",
        json={"status": "rejected"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_private_document_view_url_requires_staff_or_owner(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = _under_review_artist(db_session)
    stranger = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(
        f"/api/v1/admin/artists/{artist_profile.id}/documents", headers=auth_headers(token)
    )

    assert response.status_code == 403
