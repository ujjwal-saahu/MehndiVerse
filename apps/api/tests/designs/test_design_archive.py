from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_design, make_user


def test_archive_design_requires_authentication(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session)
    db_session.commit()

    response = client.post(f"/api/v1/designs/{design.id}/archive")

    assert response.status_code == 401


def test_owner_can_archive_a_draft_design(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="archiver@example.com")

    response = client.post(f"/api/v1/designs/{design.id}/archive", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_owner_can_archive_a_published_design(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile, status="published")
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="archiver2@example.com")

    response = client.post(f"/api/v1/designs/{design.id}/archive", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_cannot_archive_an_already_archived_design(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile, status="archived")
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="archiver3@example.com")

    response = client.post(f"/api/v1/designs/{design.id}/archive", headers=auth_headers(token))

    assert response.status_code == 422


def test_non_owner_cannot_archive_design(client: TestClient, db_session: Session) -> None:
    owner_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=owner_profile)
    other_user = make_user(db_session)
    db_session.commit()
    token = sign_token(other_user.id, email=other_user.email)

    response = client.post(f"/api/v1/designs/{design.id}/archive", headers=auth_headers(token))

    assert response.status_code == 403


def test_archive_unknown_design_is_404(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/designs/00000000-0000-0000-0000-000000000000/archive",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
