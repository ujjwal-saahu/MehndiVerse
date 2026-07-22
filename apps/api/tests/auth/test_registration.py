import uuid

import httpx
import respx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user import Profile, User


def test_registration_requires_email_confirmation_creates_local_customer(
    client: TestClient, supabase_mock: respx.MockRouter, db_session: Session
) -> None:
    new_user_id = str(uuid.uuid4())
    supabase_mock.post("/signup").mock(
        return_value=httpx.Response(
            200,
            json={"id": new_user_id, "email": "new@example.com", "email_confirmed_at": None},
        )
    )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "password": "supersecret123",
            "terms_accepted": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["session"] is None
    assert "verify" in body["message"].lower()

    user = db_session.get(User, uuid.UUID(new_user_id))
    assert user is not None
    assert user.role == "customer"
    assert user.email == "new@example.com"

    profile = db_session.execute(
        select(Profile).where(Profile.user_id == user.id)
    ).scalar_one_or_none()
    assert profile is not None


def test_registration_with_immediate_session_returns_tokens(
    client: TestClient, supabase_mock: respx.MockRouter, db_session: Session
) -> None:
    new_user_id = str(uuid.uuid4())
    supabase_mock.post("/signup").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "at-123",
                "refresh_token": "rt-123",
                "expires_in": 3600,
                "user": {
                    "id": new_user_id,
                    "email": "confirmed@example.com",
                    "email_confirmed_at": "2026-01-01T00:00:00Z",
                },
            },
        )
    )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "confirmed@example.com",
            "password": "supersecret123",
            "terms_accepted": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["session"]["access_token"] == "at-123"
    assert body["session"]["refresh_token"] == "rt-123"


def test_registration_ignores_client_sent_role(
    client: TestClient, supabase_mock: respx.MockRouter, db_session: Session
) -> None:
    new_user_id = str(uuid.uuid4())
    supabase_mock.post("/signup").mock(
        return_value=httpx.Response(
            200,
            json={"id": new_user_id, "email": "sneaky@example.com", "email_confirmed_at": None},
        )
    )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "sneaky@example.com",
            "password": "supersecret123",
            "role": "super_administrator",
            "terms_accepted": True,
        },
    )

    assert response.status_code == 201
    user = db_session.get(User, uuid.UUID(new_user_id))
    assert user is not None
    assert user.role == "customer"


def test_registration_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register", json={"email": "short@example.com", "password": "abc"}
    )
    assert response.status_code == 422


def test_registration_maps_supabase_error(
    client: TestClient, supabase_mock: respx.MockRouter
) -> None:
    supabase_mock.post("/signup").mock(
        return_value=httpx.Response(422, json={"error_description": "User already registered"})
    )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@example.com",
            "password": "supersecret123",
            "terms_accepted": True,
        },
    )

    assert response.status_code == 422
    assert "already registered" in response.json()["error"]["message"].lower()


def test_registration_rate_limited(client: TestClient, supabase_mock: respx.MockRouter) -> None:
    # Same user id on every call: Supabase itself would return the existing
    # user for a repeat signup attempt with the same email, and this test
    # only cares about the rate limiter, not repeated-signup semantics.
    fixed_user_id = str(uuid.uuid4())
    supabase_mock.post("/signup").mock(
        return_value=httpx.Response(
            200,
            json={"id": fixed_user_id, "email": "rate@example.com", "email_confirmed_at": None},
        )
    )

    statuses = [
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "rate@example.com",
                "password": "supersecret123",
                "terms_accepted": True,
            },
        ).status_code
        for _ in range(6)
    ]

    assert statuses[:5] == [201, 201, 201, 201, 201]
    assert statuses[5] == 429


def test_registration_requires_terms_acceptance(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "noterms@example.com", "password": "supersecret123"},
    )
    assert response.status_code == 422
    assert "terms" in response.json()["error"]["message"].lower()


def test_registration_records_terms_and_privacy_consent(
    client: TestClient, supabase_mock: respx.MockRouter, db_session: Session
) -> None:
    from app.db.enums import ConsentType
    from app.db.models.support import ConsentRecord

    new_user_id = str(uuid.uuid4())
    supabase_mock.post("/signup").mock(
        return_value=httpx.Response(
            200,
            json={"id": new_user_id, "email": "consenter@example.com", "email_confirmed_at": None},
        )
    )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "consenter@example.com",
            "password": "supersecret123",
            "terms_accepted": True,
        },
    )
    assert response.status_code == 201

    records = (
        db_session.execute(
            select(ConsentRecord).where(ConsentRecord.user_id == uuid.UUID(new_user_id))
        )
        .scalars()
        .all()
    )
    consent_types = {record.consent_type for record in records}
    assert consent_types == {ConsentType.TERMS_OF_SERVICE.value, ConsentType.PRIVACY_POLICY.value}
    assert all(record.granted for record in records)
