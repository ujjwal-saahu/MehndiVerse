import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import UserRole
from app.db.models.user import User
from tests.auth.conftest import auth_headers, sign_token


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user_for_valid_token(client: TestClient, db_session: Session) -> None:
    user = User(id=uuid.uuid4(), email="me@example.com", role=UserRole.CUSTOMER.value)
    db_session.add(user)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/auth/me", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["email"] == "me@example.com"
    assert body["role"] == "customer"


def test_me_never_trusts_the_jwt_internal_role_claim(
    client: TestClient, db_session: Session
) -> None:
    """The signed token always carries Supabase's internal `role:
    authenticated` claim (see sign_token()) — the effective role returned
    must come from the users table, not from anything in the token."""
    user = User(id=uuid.uuid4(), email="admin-ish@example.com", role=UserRole.ADMINISTRATOR.value)
    db_session.add(user)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/auth/me", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_lazy_provisions_local_user_on_first_valid_token(
    client: TestClient, db_session: Session
) -> None:
    """A token can be valid (signed by Supabase for a real auth.users row)
    before our register endpoint has ever been called for that id — e.g. if
    an account is created directly against Supabase. The dependency should
    provision a local row rather than reject the request."""
    unseen_user_id = uuid.uuid4()
    token = sign_token(unseen_user_id, email="brand-new@example.com")

    response = client.get("/api/v1/auth/me", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["role"] == "customer"
    assert db_session.get(User, unseen_user_id) is not None


def test_deleted_account_cannot_authenticate(client: TestClient, db_session: Session) -> None:
    user = User(id=uuid.uuid4(), email="gone@example.com", role=UserRole.CUSTOMER.value)
    db_session.add(user)
    db_session.flush()
    user.deleted_at = datetime.now(UTC)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/auth/me", headers=auth_headers(token))

    assert response.status_code == 401
