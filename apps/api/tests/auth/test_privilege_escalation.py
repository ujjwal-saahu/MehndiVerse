import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.authz import can_grant_role
from app.db.enums import UserRole
from app.db.models.user import User
from tests.auth.conftest import auth_headers, sign_token


def _make_user(db_session: Session, role: str, email: str) -> User:
    user = User(id=uuid.uuid4(), email=email, role=role)
    db_session.add(user)
    db_session.commit()
    return user


def test_admin_cannot_change_their_own_role(client: TestClient, db_session: Session) -> None:
    admin = _make_user(db_session, UserRole.ADMINISTRATOR.value, "self-admin@example.com")
    token = sign_token(admin.id, email=admin.email)

    response = client.patch(
        f"/api/v1/admin/users/{admin.id}/role",
        json={"role": "super_administrator"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403
    db_session.refresh(admin)
    assert admin.role == UserRole.ADMINISTRATOR.value


def test_super_admin_cannot_change_their_own_role_either(
    client: TestClient, db_session: Session
) -> None:
    super_admin = _make_user(
        db_session, UserRole.SUPER_ADMINISTRATOR.value, "self-super@example.com"
    )
    token = sign_token(super_admin.id, email=super_admin.email)

    response = client.patch(
        f"/api/v1/admin/users/{super_admin.id}/role",
        json={"role": "administrator"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_administrator_cannot_grant_administrator_role(
    client: TestClient, db_session: Session
) -> None:
    """Only a super_admin may mint another admin — see docs/authentication.md#3."""
    admin = _make_user(db_session, UserRole.ADMINISTRATOR.value, "grantor@example.com")
    target = _make_user(db_session, UserRole.CUSTOMER.value, "grantee@example.com")
    token = sign_token(admin.id, email=admin.email)

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "administrator"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403
    db_session.refresh(target)
    assert target.role == UserRole.CUSTOMER.value


def test_administrator_cannot_grant_super_administrator_role(
    client: TestClient, db_session: Session
) -> None:
    admin = _make_user(db_session, UserRole.ADMINISTRATOR.value, "grantor2@example.com")
    target = _make_user(db_session, UserRole.CUSTOMER.value, "grantee2@example.com")
    token = sign_token(admin.id, email=admin.email)

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "super_administrator"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_super_administrator_can_grant_administrator_role(
    client: TestClient, db_session: Session
) -> None:
    super_admin = _make_user(db_session, UserRole.SUPER_ADMINISTRATOR.value, "super@example.com")
    target = _make_user(db_session, UserRole.CUSTOMER.value, "grantee3@example.com")
    token = sign_token(super_admin.id, email=super_admin.email)

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "administrator"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_unknown_role_value_is_rejected(client: TestClient, db_session: Session) -> None:
    super_admin = _make_user(db_session, UserRole.SUPER_ADMINISTRATOR.value, "super2@example.com")
    target = _make_user(db_session, UserRole.CUSTOMER.value, "grantee4@example.com")
    token = sign_token(super_admin.id, email=super_admin.email)

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "godmode"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_can_grant_role_matrix() -> None:
    """Pure-logic cross-check of the grant matrix backing the endpoint tests
    above — see app/core/authz.py."""
    assert can_grant_role(grantor_role="super_administrator", target_role="administrator")
    assert can_grant_role(grantor_role="super_administrator", target_role="super_administrator")
    assert can_grant_role(grantor_role="administrator", target_role="moderator")
    assert not can_grant_role(grantor_role="administrator", target_role="administrator")
    assert not can_grant_role(grantor_role="administrator", target_role="super_administrator")
    assert not can_grant_role(grantor_role="moderator", target_role="customer")
    assert not can_grant_role(grantor_role="customer", target_role="customer")
