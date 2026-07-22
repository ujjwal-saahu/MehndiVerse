import uuid

import httpx
import respx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import UserRole
from app.db.models.user import User


def _mock_token_response(supabase_mock: respx.MockRouter, *, user_id: str, email: str) -> None:
    supabase_mock.post("/token", params={"grant_type": "password"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "at-login",
                "refresh_token": "rt-login",
                "expires_in": 3600,
                "user": {
                    "id": user_id,
                    "email": email,
                    "email_confirmed_at": "2026-01-01T00:00:00Z",
                },
            },
        )
    )


def test_login_returns_tokens_and_updates_last_login(
    client: TestClient, supabase_mock: respx.MockRouter, db_session: Session
) -> None:
    user = User(id=uuid.uuid4(), email="existing@example.com", role=UserRole.CUSTOMER.value)
    db_session.add(user)
    db_session.commit()
    _mock_token_response(supabase_mock, user_id=str(user.id), email=user.email)

    response = client.post(
        "/api/v1/auth/login", json={"email": "existing@example.com", "password": "correct-horse"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "at-login"
    assert body["refresh_token"] == "rt-login"

    db_session.refresh(user)
    assert user.last_login_at is not None


def test_login_with_wrong_credentials_returns_generic_401(
    client: TestClient, supabase_mock: respx.MockRouter
) -> None:
    supabase_mock.post("/token", params={"grant_type": "password"}).mock(
        return_value=httpx.Response(400, json={"error_description": "Invalid login credentials"})
    )

    response = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password."


def test_login_rate_limited(client: TestClient, supabase_mock: respx.MockRouter) -> None:
    supabase_mock.post("/token", params={"grant_type": "password"}).mock(
        return_value=httpx.Response(400, json={"error_description": "Invalid login credentials"})
    )

    statuses = [
        client.post(
            "/api/v1/auth/login", json={"email": "brute@example.com", "password": "guess"}
        ).status_code
        for _ in range(6)
    ]

    assert statuses[:5] == [401, 401, 401, 401, 401]
    assert statuses[5] == 429
