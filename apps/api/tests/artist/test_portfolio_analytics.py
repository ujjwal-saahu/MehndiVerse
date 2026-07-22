from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_design, make_user


def test_analytics_requires_an_artist_profile(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, role="artist")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/artist/portfolio/analytics", headers=auth_headers(token))

    assert response.status_code == 404


def test_analytics_aggregates_across_the_artists_own_designs(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    published = make_design(db_session, artist_profile=profile, status="published")
    published.view_count = 100
    published.like_count = 10
    published.save_count = 5
    make_design(db_session, artist_profile=profile, status="draft")
    other_profile = make_artist_profile(db_session)
    other_design = make_design(db_session, artist_profile=other_profile, status="published")
    other_design.view_count = 999  # must not leak into this artist's totals
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get("/api/v1/artist/portfolio/analytics", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["total_designs"] == 2
    assert body["published_designs"] == 1
    assert body["total_views"] == 100
    assert body["total_likes"] == 10
    assert body["total_saves"] == 5
    assert len(body["top_designs"]) == 2
    assert body["top_designs"][0]["view_count"] == 100


def test_analytics_with_no_designs_is_all_zero(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get("/api/v1/artist/portfolio/analytics", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["total_designs"] == 0
    assert body["total_views"] == 0
    assert body["top_designs"] == []
