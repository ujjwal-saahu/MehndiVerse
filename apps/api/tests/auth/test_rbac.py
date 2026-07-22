import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import UserRole
from app.db.models.user import User
from tests.auth.conftest import auth_headers, sign_token


def _make_user(db_session: Session, role: str, email: str) -> User:
    user = User(id=uuid.uuid4(), email=email, role=role)
    db_session.add(user)
    db_session.commit()
    return user


def test_customer_cannot_access_admin_role_endpoint(
    client: TestClient, db_session: Session
) -> None:
    customer = _make_user(db_session, UserRole.CUSTOMER.value, "customer@example.com")
    target = _make_user(db_session, UserRole.CUSTOMER.value, "target@example.com")
    token = sign_token(customer.id, email=customer.email)

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "artist"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_moderator_cannot_access_admin_role_endpoint(
    client: TestClient, db_session: Session
) -> None:
    """Moderator is a staff role but not admin/super_admin — role management
    is out of its scope (see docs/user-roles-and-permissions.md)."""
    moderator = _make_user(db_session, UserRole.MODERATOR.value, "mod@example.com")
    target = _make_user(db_session, UserRole.CUSTOMER.value, "target2@example.com")
    token = sign_token(moderator.id, email=moderator.email)

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "artist"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_administrator_can_grant_moderator_role(client: TestClient, db_session: Session) -> None:
    admin = _make_user(db_session, UserRole.ADMINISTRATOR.value, "admin@example.com")
    target = _make_user(db_session, UserRole.CUSTOMER.value, "target3@example.com")
    token = sign_token(admin.id, email=admin.email)

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "moderator"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "moderator"


def test_unauthenticated_request_is_rejected(client: TestClient, db_session: Session) -> None:
    target = _make_user(db_session, UserRole.CUSTOMER.value, "target4@example.com")

    response = client.patch(f"/api/v1/admin/users/{target.id}/role", json={"role": "artist"})

    assert response.status_code == 401
