"""Account-based login-abuse protection — see
docs/security-review.md#login-abuse-protection and
app/services/login_security.py. `_reset_rate_limiter` (tests/auth/
conftest.py) flushes the Redis lockout keys before/after every test, so
these don't leak into each other."""

import uuid

import httpx
import respx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import limiter
from app.core.config import get_settings
from app.db.enums import UserRole
from app.db.models.system import AuditLog
from app.db.models.user import User
from app.services.login_security import is_locked_out


def _mock_bad_password(supabase_mock: respx.MockRouter) -> None:
    supabase_mock.post("/token", params={"grant_type": "password"}).mock(
        return_value=httpx.Response(400, json={"error_description": "Invalid login credentials"})
    )


def test_account_is_not_locked_out_before_threshold(
    client: TestClient, supabase_mock: respx.MockRouter, db_session: Session
) -> None:
    _mock_bad_password(supabase_mock)
    threshold = get_settings().login_lockout_threshold

    for _ in range(threshold - 1):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "notyet@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    assert not is_locked_out("notyet@example.com")


def test_account_is_locked_out_after_threshold_failures(
    client: TestClient, supabase_mock: respx.MockRouter, db_session: Session
) -> None:
    _mock_bad_password(supabase_mock)
    threshold = get_settings().login_lockout_threshold

    for _ in range(threshold):
        client.post(
            "/api/v1/auth/login",
            json={"email": "locked@example.com", "password": "wrong"},
        )

    assert is_locked_out("locked@example.com")

    # Isolate the account-lockout check from the IP-based rate limit (both
    # default to the same threshold, so without this the next request would
    # get a 429 from slowapi before ever reaching the lockout check).
    limiter.reset()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "locked@example.com", "password": "maybe-correct-this-time"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password."


def test_lockout_records_an_audit_event_exactly_once(
    client: TestClient, supabase_mock: respx.MockRouter, db_session: Session
) -> None:
    _mock_bad_password(supabase_mock)
    threshold = get_settings().login_lockout_threshold

    for _ in range(threshold + 2):
        client.post(
            "/api/v1/auth/login",
            json={"email": "noisy@example.com", "password": "wrong"},
        )

    events = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "login.lockout_triggered"))
        .scalars()
        .all()
    )
    matching = [
        e for e in events if e.after_state and e.after_state.get("email") == "noisy@example.com"
    ]
    assert len(matching) == 1


def test_successful_login_clears_the_failure_counter(
    client: TestClient, supabase_mock: respx.MockRouter, db_session: Session
) -> None:
    user = User(id=uuid.uuid4(), email="recovers@example.com", role=UserRole.CUSTOMER.value)
    db_session.add(user)
    db_session.commit()

    _mock_bad_password(supabase_mock)
    client.post("/api/v1/auth/login", json={"email": "recovers@example.com", "password": "wrong"})
    client.post("/api/v1/auth/login", json={"email": "recovers@example.com", "password": "wrong"})

    supabase_mock.reset()
    supabase_mock.post("/token", params={"grant_type": "password"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "at",
                "refresh_token": "rt",
                "expires_in": 3600,
                "user": {"id": str(user.id), "email": user.email},
            },
        )
    )
    response = client.post(
        "/api/v1/auth/login", json={"email": "recovers@example.com", "password": "correct"}
    )
    assert response.status_code == 200
    assert not is_locked_out("recovers@example.com")
