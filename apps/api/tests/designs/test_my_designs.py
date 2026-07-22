from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_design, make_user


def test_list_my_designs_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/designs/mine")
    assert response.status_code == 401


def test_list_my_designs_requires_an_artist_profile(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, role="artist")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/designs/mine", headers=auth_headers(token))

    assert response.status_code == 404


def test_list_my_designs_returns_every_status_but_only_the_owners(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    make_design(db_session, artist_profile=profile, status="draft")
    make_design(db_session, artist_profile=profile, status="published")
    make_design(db_session, artist_profile=profile, status="archived")
    other_profile = make_artist_profile(db_session)
    make_design(db_session, artist_profile=other_profile, status="published")
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get("/api/v1/designs/mine", headers=auth_headers(token))

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 3
    assert {item["status"] for item in items} == {"draft", "published", "archived"}


def test_list_my_designs_status_filter(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    make_design(db_session, artist_profile=profile, status="draft")
    make_design(db_session, artist_profile=profile, status="published")
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get(
        "/api/v1/designs/mine", params={"status_filter": "draft"}, headers=auth_headers(token)
    )

    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "draft"


def test_list_my_designs_rejects_unknown_status_filter(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get(
        "/api/v1/designs/mine", params={"status_filter": "bogus"}, headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_list_my_designs_pagination(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    for _ in range(3):
        make_design(db_session, artist_profile=profile, status="draft")
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    first_page = client.get(
        "/api/v1/designs/mine", params={"limit": 2}, headers=auth_headers(token)
    ).json()
    assert len(first_page["items"]) == 2
    assert first_page["page_info"]["has_more"] is True

    second_page = client.get(
        "/api/v1/designs/mine",
        params={"limit": 2, "cursor": first_page["page_info"]["next_cursor"]},
        headers=auth_headers(token),
    ).json()
    assert len(second_page["items"]) == 1
    assert second_page["page_info"]["has_more"] is False
