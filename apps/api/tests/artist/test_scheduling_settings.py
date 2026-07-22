from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile


def test_get_settings_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/artist/availability/settings")
    assert response.status_code == 401


def test_get_default_settings(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.get("/api/v1/artist/availability/settings", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == "UTC"
    assert body["default_buffer_minutes"] == 0
    assert body["default_travel_buffer_minutes"] == 0


def test_update_settings(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.patch(
        "/api/v1/artist/availability/settings",
        json={
            "timezone": "Asia/Kolkata",
            "default_buffer_minutes": 15,
            "default_travel_buffer_minutes": 30,
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == "Asia/Kolkata"
    assert body["default_buffer_minutes"] == 15
    assert body["default_travel_buffer_minutes"] == 30


def test_update_settings_rejects_unknown_timezone(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.patch(
        "/api/v1/artist/availability/settings",
        json={"timezone": "Not/AZone"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_update_settings_rejects_negative_buffer(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.patch(
        "/api/v1/artist/availability/settings",
        json={"default_buffer_minutes": -5},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
