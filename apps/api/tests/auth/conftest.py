import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import limiter
from app.core.config import get_settings
from app.core.redis_client import get_redis_client
from app.db.session import get_db_session
from app.main import app


def sign_token(
    user_id: uuid.UUID | str,
    *,
    email: str | None = "person@example.com",
    expires_in: timedelta = timedelta(hours=1),
    secret: str | None = None,
    audience: str = "authenticated",
) -> str:
    """Signs a Supabase-shaped access token. `role: authenticated` is
    Supabase's internal Postgres-role claim, included deliberately so tests
    can confirm the app never treats it as the application role."""
    settings = get_settings()
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "aud": audience,
        "role": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + expires_in).timestamp()),
    }
    return jwt.encode(claims, secret or settings.supabase_jwt_secret, algorithm="HS256")


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def mock_reauth_ok(supabase_mock: respx.MockRouter, *, email: str, user_id: uuid.UUID) -> None:
    """Mocks the Supabase password-grant call `_verify_reauth`
    (app/api/routes/auth.py) makes — shared by every test that exercises a
    reauth-gated endpoint (account deletion, session revoke-all)."""
    supabase_mock.post("/token", params={"grant_type": "password"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "reauth-at",
                "refresh_token": "reauth-rt",
                "expires_in": 3600,
                "user": {"id": str(user_id), "email": email},
            },
        )
    )


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_db_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _flush_login_lockout_keys() -> None:
    client = get_redis_client()
    keys = list(client.scan_iter(match="login_fail:*"))
    if keys:
        client.delete(*keys)


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> Generator[None, None, None]:
    limiter.reset()
    _flush_login_lockout_keys()
    yield
    limiter.reset()
    _flush_login_lockout_keys()


@pytest.fixture
def supabase_mock() -> Generator[respx.MockRouter, None, None]:
    settings = get_settings()
    with respx.mock(base_url=f"{settings.supabase_url}/auth/v1") as router:
        yield router
