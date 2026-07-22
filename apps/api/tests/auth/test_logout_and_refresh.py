import uuid

import httpx
import respx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import UserRole
from app.db.models.user import User
from tests.auth.conftest import auth_headers, sign_token


def test_logout_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 401


def test_logout_calls_supabase_and_succeeds(
    client: TestClient, supabase_mock: respx.MockRouter, db_session: Session
) -> None:
    user = User(id=uuid.uuid4(), email="logout@example.com", role=UserRole.CUSTOMER.value)
    db_session.add(user)
    db_session.commit()
    token = sign_token(user.id, email=user.email)
    logout_route = supabase_mock.post("/logout").mock(return_value=httpx.Response(204))

    response = client.post("/api/v1/auth/logout", headers=auth_headers(token))

    assert response.status_code == 204
    assert logout_route.called


def test_refresh_returns_new_tokens(client: TestClient, supabase_mock: respx.MockRouter) -> None:
    supabase_mock.post("/token", params={"grant_type": "refresh_token"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "at-refreshed",
                "refresh_token": "rt-refreshed",
                "expires_in": 3600,
                "user": {"id": str(uuid.uuid4()), "email": "x@example.com"},
            },
        )
    )

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "rt-old"})

    assert response.status_code == 200
    assert response.json()["access_token"] == "at-refreshed"


def test_refresh_with_invalid_token_is_rejected(
    client: TestClient, supabase_mock: respx.MockRouter
) -> None:
    supabase_mock.post("/token", params={"grant_type": "refresh_token"}).mock(
        return_value=httpx.Response(400, json={"error_description": "Invalid Refresh Token"})
    )

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})

    assert response.status_code == 401
