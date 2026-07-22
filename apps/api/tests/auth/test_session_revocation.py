"""`POST /auth/sessions/revoke-all` — see docs/security-review.md#session-
revocation."""

import uuid

import httpx
import respx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import UserRole
from app.db.models.system import AuditLog
from app.db.models.user import User
from tests.auth.conftest import auth_headers, mock_reauth_ok, sign_token


def test_revoke_all_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/auth/sessions/revoke-all", json={"password": "whatever123"})
    assert response.status_code == 401


def test_revoke_all_requires_correct_password(
    client: TestClient, db_session: Session, supabase_mock: respx.MockRouter
) -> None:
    user = User(id=uuid.uuid4(), email="reauth@example.com", role=UserRole.CUSTOMER.value)
    db_session.add(user)
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    supabase_mock.post("/token", params={"grant_type": "password"}).mock(
        return_value=httpx.Response(400, json={"error_description": "Invalid login credentials"})
    )

    response = client.post(
        "/api/v1/auth/sessions/revoke-all",
        json={"password": "wrong"},
        headers=auth_headers(token),
    )

    assert response.status_code == 401


def test_revoke_all_calls_supabase_with_global_scope_and_audits(
    client: TestClient, db_session: Session, supabase_mock: respx.MockRouter
) -> None:
    user = User(id=uuid.uuid4(), email="revoke@example.com", role=UserRole.CUSTOMER.value)
    db_session.add(user)
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    mock_reauth_ok(supabase_mock, email=user.email, user_id=user.id)
    logout_route = supabase_mock.post("/logout", params={"scope": "global"}).mock(
        return_value=httpx.Response(204)
    )

    response = client.post(
        "/api/v1/auth/sessions/revoke-all",
        json={"password": "correct-password"},
        headers=auth_headers(token),
    )

    assert response.status_code == 204
    assert logout_route.called

    events = (
        db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "session.revoke_all", AuditLog.actor_id == user.id
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
