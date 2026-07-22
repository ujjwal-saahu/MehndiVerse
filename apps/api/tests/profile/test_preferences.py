from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_user


def test_get_preferences_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/users/me/preferences")
    assert response.status_code == 401


def test_get_preferences_returns_defaults_when_missing(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, email="prefs-default@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/users/me/preferences", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["email_notifications"] is True
    assert body["profile_visibility"] == "public"
    assert body["show_location"] is True
    assert body["allow_messages_from_strangers"] is True


def test_update_preferences_applies_only_provided_fields(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, email="prefs-update@example.com")
    token = sign_token(user.id, email=user.email)
    client.get("/api/v1/users/me/preferences", headers=auth_headers(token))

    response = client.patch(
        "/api/v1/users/me/preferences",
        json={"push_notifications": False, "profile_visibility": "private"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["push_notifications"] is False
    assert body["profile_visibility"] == "private"
    assert body["email_notifications"] is True  # untouched


def test_update_preferences_rejects_invalid_visibility(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, email="prefs-badvis@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.patch(
        "/api/v1/users/me/preferences",
        json={"profile_visibility": "hidden"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
