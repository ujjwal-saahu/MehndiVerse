from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_category, make_design, make_user


def test_suggestions_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/designs/search/suggestions", params={"q": "hen"})
    assert response.status_code == 401


def test_suggestions_returns_matching_design_titles(
    client: TestClient, db_session: Session
) -> None:
    matching = make_design(db_session, status="published")
    matching.title = "Henna Bridal Set"
    non_matching = make_design(db_session, status="published")
    non_matching.title = "Floral Pattern"
    db_session.add_all([matching, non_matching])
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(
        "/api/v1/designs/search/suggestions", params={"q": "henn"}, headers=auth_headers(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert any(hit["type"] == "design" and hit["label"] == "Henna Bridal Set" for hit in body)
    assert not any(hit["label"] == "Floral Pattern" for hit in body)


def test_suggestions_include_categories_and_artists(
    client: TestClient, db_session: Session
) -> None:
    make_category(db_session, name="Arabesque")
    artist = make_artist_profile(db_session)
    artist.business_name = "Arabesque Art Studio"
    db_session.add(artist)
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(
        "/api/v1/designs/search/suggestions", params={"q": "arabe"}, headers=auth_headers(token)
    )

    assert response.status_code == 200
    types = {hit["type"] for hit in response.json()}
    assert "category" in types
    assert "artist" in types


def test_suggestions_below_minimum_length_returns_empty(
    client: TestClient, db_session: Session
) -> None:
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(
        "/api/v1/designs/search/suggestions", params={"q": "a"}, headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json() == []


def test_suggestions_only_include_published_designs(
    client: TestClient, db_session: Session
) -> None:
    draft = make_design(db_session, status="draft")
    draft.title = "Hennadraft Sketch"
    db_session.add(draft)
    viewer = make_user(db_session)
    db_session.commit()
    token = sign_token(viewer.id, email=viewer.email)

    response = client.get(
        "/api/v1/designs/search/suggestions",
        params={"q": "hennadraft"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == []
