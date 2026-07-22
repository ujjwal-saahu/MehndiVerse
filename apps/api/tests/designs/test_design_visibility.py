from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import UserRole
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_design, make_user


def test_get_design_requires_authentication(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    db_session.commit()

    response = client.get(f"/api/v1/designs/{design.id}")

    assert response.status_code == 401


def test_published_design_detail_sets_a_safe_public_cache_header(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.headers["cache-control"].startswith("public")


def test_draft_design_detail_is_never_publicly_cached(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    draft = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="cacheowner@example.com")

    response = client.get(f"/api/v1/designs/{draft.id}", headers=auth_headers(token))

    assert response.status_code == 200
    assert "cache-control" not in response.headers


def test_anyone_can_view_a_published_design(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    stranger = make_user(db_session)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))

    assert response.status_code == 200


def test_draft_design_is_hidden_from_strangers(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    stranger = make_user(db_session)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))

    assert response.status_code == 404


def test_draft_design_is_visible_to_its_owner(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="owner@example.com")

    response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))

    assert response.status_code == 200


def test_draft_design_is_visible_to_moderator(client: TestClient, db_session: Session) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile)
    moderator = make_user(db_session, role=UserRole.MODERATOR.value)
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))

    assert response.status_code == 200


def test_get_unknown_design_is_404(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    token = sign_token(user.id, email=user.email)

    response = client.get(
        "/api/v1/designs/00000000-0000-0000-0000-000000000000", headers=auth_headers(token)
    )

    assert response.status_code == 404


def test_list_published_designs_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/designs/published")
    assert response.status_code == 401


def test_list_published_designs_excludes_drafts_and_archived(
    client: TestClient, db_session: Session
) -> None:
    make_design(db_session, status="published")
    make_design(db_session, status="draft")
    make_design(db_session, status="archived")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get("/api/v1/designs/published", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()["items"]
    assert len(body) == 1
    assert body[0]["status"] == "published"


def test_list_published_designs_excludes_flagged(client: TestClient, db_session: Session) -> None:
    make_design(db_session, status="flagged")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get("/api/v1/designs/published", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_list_published_designs_filters_by_difficulty(
    client: TestClient, db_session: Session
) -> None:
    easy = make_design(db_session, status="published")
    easy.difficulty_level = "beginner"
    hard = make_design(db_session, status="published")
    hard.difficulty_level = "advanced"
    db_session.add_all([easy, hard])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(
        "/api/v1/designs/published",
        params={"difficulty_level": "advanced"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()["items"]
    assert len(body) == 1
    assert body[0]["id"] == str(hard.id)
