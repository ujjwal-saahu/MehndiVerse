"""Notification history API — see docs/booking-messaging.md#3c."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_notification, make_user


def test_list_notifications_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/notifications")
    assert response.status_code == 401


def test_list_my_notifications(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    other = make_user(db_session)
    make_notification(db_session, user=user, title="Mine")
    make_notification(db_session, user=other, title="Not mine")
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/notifications", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "Mine"
    assert body["unread_count"] == 1


def test_unread_only_filter(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    make_notification(db_session, user=user, title="Read one", is_read=True)
    make_notification(db_session, user=user, title="Unread one", is_read=False)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get(
        "/api/v1/notifications", params={"unread_only": True}, headers=auth_headers(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "Unread one"


def test_unread_count_endpoint(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    make_notification(db_session, user=user, is_read=False)
    make_notification(db_session, user=user, is_read=False)
    make_notification(db_session, user=user, is_read=True)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/notifications/unread-count", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["unread_count"] == 2


def test_mark_one_notification_read(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    notification = make_notification(db_session, user=user, is_read=False)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        f"/api/v1/notifications/{notification.id}/read", headers=auth_headers(token)
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True
    assert response.json()["read_at"] is not None


def test_cannot_mark_someone_elses_notification_read(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    other = make_user(db_session)
    notification = make_notification(db_session, user=other, is_read=False)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        f"/api/v1/notifications/{notification.id}/read", headers=auth_headers(token)
    )
    assert response.status_code == 403


def test_mark_all_notifications_read(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    make_notification(db_session, user=user, is_read=False)
    make_notification(db_session, user=user, is_read=False)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post("/api/v1/notifications/read-all", headers=auth_headers(token))
    assert response.status_code == 204

    unread = client.get("/api/v1/notifications/unread-count", headers=auth_headers(token)).json()
    assert unread["unread_count"] == 0


def test_mark_unknown_notification_read_is_404(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/notifications/00000000-0000-0000-0000-000000000000/read",
        headers=auth_headers(token),
    )
    assert response.status_code == 404
