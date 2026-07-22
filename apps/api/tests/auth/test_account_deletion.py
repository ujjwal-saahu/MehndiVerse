import uuid

import httpx
import respx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import UserRole, UserStatus
from app.db.models.user import User
from tests.auth.conftest import auth_headers, mock_reauth_ok, sign_token


def test_account_deletion_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/account/deletion-request", json={"password": "whatever123"}
    )
    assert response.status_code == 401


def test_authenticated_user_can_request_account_deletion(
    client: TestClient, db_session: Session, supabase_mock: respx.MockRouter
) -> None:
    user = User(id=uuid.uuid4(), email="leaving@example.com", role=UserRole.CUSTOMER.value)
    db_session.add(user)
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    mock_reauth_ok(supabase_mock, email=user.email, user_id=user.id)

    response = client.post(
        "/api/v1/auth/account/deletion-request",
        json={"password": "correct-password"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["deletion_requested_at"] is not None

    db_session.refresh(user)
    assert user.status == UserStatus.PENDING_DELETION.value
    assert user.deletion_requested_at is not None
    # Soft-delete only — the row itself is never removed by this endpoint.
    assert user.deleted_at is None


def test_account_deletion_requires_correct_password(
    client: TestClient, db_session: Session, supabase_mock: respx.MockRouter
) -> None:
    user = User(id=uuid.uuid4(), email="wrongpw@example.com", role=UserRole.CUSTOMER.value)
    db_session.add(user)
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    supabase_mock.post("/token", params={"grant_type": "password"}).mock(
        return_value=httpx.Response(400, json={"error_description": "Invalid login credentials"})
    )

    response = client.post(
        "/api/v1/auth/account/deletion-request",
        json={"password": "wrong-password"},
        headers=auth_headers(token),
    )

    assert response.status_code == 401
    db_session.refresh(user)
    assert user.deletion_requested_at is None


def test_duplicate_deletion_request_is_rejected(
    client: TestClient, db_session: Session, supabase_mock: respx.MockRouter
) -> None:
    user = User(id=uuid.uuid4(), email="twice@example.com", role=UserRole.CUSTOMER.value)
    db_session.add(user)
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    mock_reauth_ok(supabase_mock, email=user.email, user_id=user.id)

    first = client.post(
        "/api/v1/auth/account/deletion-request",
        json={"password": "correct-password"},
        headers=auth_headers(token),
    )
    second = client.post(
        "/api/v1/auth/account/deletion-request",
        json={"password": "correct-password"},
        headers=auth_headers(token),
    )

    assert first.status_code == 200
    assert second.status_code == 409
