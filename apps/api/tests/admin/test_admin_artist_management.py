from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import ArtistVerificationStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_user


def _token(db_session: Session, *, role: str):
    user = make_user(db_session, role=role)
    db_session.commit()
    return user, sign_token(user.id, email=user.email)


def _suspended_artist(db_session: Session):
    profile = make_artist_profile(db_session)
    profile.verification_status = ArtistVerificationStatus.SUSPENDED.value
    db_session.add(profile)
    db_session.commit()
    return profile


def test_status_filter_can_browse_every_artist_not_just_the_queue(
    client: TestClient, db_session: Session
) -> None:
    approved = make_artist_profile(db_session)
    approved.verification_status = ArtistVerificationStatus.APPROVED.value
    db_session.add(approved)
    db_session.commit()
    _, moderator_token = _token(db_session, role="moderator")

    response = client.get(
        "/api/v1/admin/artists",
        params={"status_filter": ["approved"]},
        headers=auth_headers(moderator_token),
    )

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert str(approved.id) in ids


def test_search_filters_by_professional_name(client: TestClient, db_session: Session) -> None:
    match = make_artist_profile(db_session)
    match.professional_name = "Priya Henna Art"
    match.verification_status = ArtistVerificationStatus.APPROVED.value
    other = make_artist_profile(db_session)
    other.professional_name = "Rohan Mehndi"
    other.verification_status = ArtistVerificationStatus.APPROVED.value
    db_session.add_all([match, other])
    db_session.commit()
    _, moderator_token = _token(db_session, role="moderator")

    response = client.get(
        "/api/v1/admin/artists",
        params={"status_filter": ["approved"], "search": "priya"},
        headers=auth_headers(moderator_token),
    )

    ids = {item["id"] for item in response.json()["items"]}
    assert ids == {str(match.id)}


def test_moderator_cannot_reactivate_artist(client: TestClient, db_session: Session) -> None:
    profile = _suspended_artist(db_session)
    _, moderator_token = _token(db_session, role="moderator")

    response = client.post(
        f"/api/v1/admin/artists/{profile.id}/reactivate", headers=auth_headers(moderator_token)
    )

    assert response.status_code == 403


def test_admin_can_reactivate_a_suspended_artist(client: TestClient, db_session: Session) -> None:
    profile = _suspended_artist(db_session)
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/artists/{profile.id}/reactivate", headers=auth_headers(admin_token)
    )

    assert response.status_code == 200
    assert response.json()["verification_status"] == "approved"


def test_cannot_reactivate_an_artist_who_is_not_suspended(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    profile.verification_status = ArtistVerificationStatus.APPROVED.value
    db_session.add(profile)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/artists/{profile.id}/reactivate", headers=auth_headers(admin_token)
    )

    assert response.status_code == 422
