import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_design, make_user


def test_view_event_requires_authentication(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    db_session.commit()

    response = client.post(f"/api/v1/designs/{design.id}/view")

    assert response.status_code == 401


def test_view_event_increments_view_count(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.post(f"/api/v1/designs/{design.id}/view", headers=auth_headers(token))
    assert response.status_code == 204

    detail = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))
    assert detail.json()["view_count"] == 1


def test_repeated_views_from_the_same_viewer_are_deduplicated(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status="published")
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    client.post(f"/api/v1/designs/{design.id}/view", headers=auth_headers(token))
    client.post(f"/api/v1/designs/{design.id}/view", headers=auth_headers(token))
    client.post(f"/api/v1/designs/{design.id}/view", headers=auth_headers(token))

    detail = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))
    assert detail.json()["view_count"] == 1


def test_different_viewers_each_count_once(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status="published")
    viewer_a = make_user(db_session)
    viewer_b = make_user(db_session)
    db_session.commit()
    token_a = sign_token(viewer_a.id, email=viewer_a.email)
    token_b = sign_token(viewer_b.id, email=viewer_b.email)

    client.post(f"/api/v1/designs/{design.id}/view", headers=auth_headers(token_a))
    client.post(f"/api/v1/designs/{design.id}/view", headers=auth_headers(token_b))

    detail = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token_a))
    assert detail.json()["view_count"] == 2


def test_viewing_your_own_draft_does_not_count_as_a_view(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    draft = make_design(db_session, artist_profile=artist_profile)
    db_session.commit()
    token = sign_token(artist_profile.user_id, email="owner@example.com")

    response = client.post(f"/api/v1/designs/{draft.id}/view", headers=auth_headers(token))
    assert response.status_code == 204

    detail = client.get(f"/api/v1/designs/{draft.id}", headers=auth_headers(token))
    assert detail.json()["view_count"] == 0


def test_view_event_on_unknown_design_is_404(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    token = sign_token(user.id, email=user.email)

    response = client.post(f"/api/v1/designs/{uuid.uuid4()}/view", headers=auth_headers(token))

    assert response.status_code == 404
