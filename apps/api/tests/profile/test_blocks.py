import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.user import Profile
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_user


def test_list_blocks_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/users/me/blocks")
    assert response.status_code == 401


def test_block_and_list_and_unblock_a_user(client: TestClient, db_session: Session) -> None:
    blocker = make_user(db_session, email="blocker@example.com")
    blocked = make_user(db_session, email="blocked@example.com")
    db_session.add(Profile(user_id=blocked.id, display_name="Annoying Person"))
    db_session.commit()
    token = sign_token(blocker.id, email=blocker.email)

    block_response = client.post(
        "/api/v1/users/me/blocks", json={"user_id": str(blocked.id)}, headers=auth_headers(token)
    )
    assert block_response.status_code == 201
    assert block_response.json()["display_name"] == "Annoying Person"

    list_response = client.get("/api/v1/users/me/blocks", headers=auth_headers(token))
    assert list_response.status_code == 200
    assert [row["user_id"] for row in list_response.json()] == [str(blocked.id)]

    unblock_response = client.delete(
        f"/api/v1/users/me/blocks/{blocked.id}", headers=auth_headers(token)
    )
    assert unblock_response.status_code == 204

    list_after = client.get("/api/v1/users/me/blocks", headers=auth_headers(token))
    assert list_after.json() == []


def test_cannot_block_self(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, email="selfblock@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/users/me/blocks", json={"user_id": str(user.id)}, headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_cannot_block_nonexistent_user(client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, email="blocknonexistent@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.post(
        "/api/v1/users/me/blocks", json={"user_id": str(uuid.uuid4())}, headers=auth_headers(token)
    )

    assert response.status_code == 404


def test_blocking_the_same_user_twice_is_rejected(client: TestClient, db_session: Session) -> None:
    blocker = make_user(db_session, email="doubleblocker@example.com")
    blocked = make_user(db_session, email="doubleblocked@example.com")
    db_session.commit()
    token = sign_token(blocker.id, email=blocker.email)

    client.post(
        "/api/v1/users/me/blocks", json={"user_id": str(blocked.id)}, headers=auth_headers(token)
    )
    response = client.post(
        "/api/v1/users/me/blocks", json={"user_id": str(blocked.id)}, headers=auth_headers(token)
    )

    assert response.status_code == 409


def test_unblocking_a_user_that_was_never_blocked_is_404(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session, email="neverblocked@example.com")
    token = sign_token(user.id, email=user.email)

    response = client.delete(f"/api/v1/users/me/blocks/{uuid.uuid4()}", headers=auth_headers(token))

    assert response.status_code == 404


def test_blocking_only_affects_the_blocker_not_the_blocked_users_view(
    client: TestClient, db_session: Session
) -> None:
    """Confirms block rows are directional and scoped to `me` — the blocked
    user's own block list is unaffected."""
    blocker = make_user(db_session, email="directional-blocker@example.com")
    blocked = make_user(db_session, email="directional-blocked@example.com")
    db_session.commit()
    blocker_token = sign_token(blocker.id, email=blocker.email)
    blocked_token = sign_token(blocked.id, email=blocked.email)

    client.post(
        "/api/v1/users/me/blocks",
        json={"user_id": str(blocked.id)},
        headers=auth_headers(blocker_token),
    )

    blocked_users_own_list = client.get(
        "/api/v1/users/me/blocks", headers=auth_headers(blocked_token)
    )
    assert blocked_users_own_list.json() == []
