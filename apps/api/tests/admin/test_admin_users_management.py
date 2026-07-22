from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.system import AuditLog
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_user


def _token(db_session: Session, *, role: str):
    user = make_user(db_session, role=role)
    db_session.commit()
    return user, sign_token(user.id, email=user.email)


def test_list_users_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 401


def test_list_users_forbidden_for_customer(client: TestClient, db_session: Session) -> None:
    _, token = _token(db_session, role="customer")

    response = client.get("/api/v1/admin/users", headers=auth_headers(token))

    assert response.status_code == 403


def test_moderator_can_list_but_not_suspend(client: TestClient, db_session: Session) -> None:
    target, _ = _token(db_session, role="customer")
    _, moderator_token = _token(db_session, role="moderator")

    list_response = client.get("/api/v1/admin/users", headers=auth_headers(moderator_token))
    assert list_response.status_code == 200

    suspend_response = client.post(
        f"/api/v1/admin/users/{target.id}/suspend",
        json={"reason": "Spamming other users"},
        headers=auth_headers(moderator_token),
    )
    assert suspend_response.status_code == 403


def test_admin_can_suspend_a_user_with_reason(client: TestClient, db_session: Session) -> None:
    target, _ = _token(db_session, role="customer")
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/users/{target.id}/suspend",
        json={"reason": "Repeated harassment reports"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "suspended"


def test_suspend_without_reason_is_rejected(client: TestClient, db_session: Session) -> None:
    target, _ = _token(db_session, role="customer")
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/users/{target.id}/suspend",
        json={"reason": ""},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 422


def test_suspend_writes_an_audit_log_entry(client: TestClient, db_session: Session) -> None:
    target, _ = _token(db_session, role="customer")
    admin, admin_token = _token(db_session, role="administrator")

    client.post(
        f"/api/v1/admin/users/{target.id}/suspend",
        json={"reason": "Repeated harassment reports"},
        headers=auth_headers(admin_token),
    )

    entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "users", AuditLog.entity_id == target.id)
        .one()
    )
    assert entry.action == "user.suspend"
    assert entry.actor_id == admin.id
    assert entry.after_state["reason"] == "Repeated harassment reports"


def test_admin_cannot_suspend_their_own_account(client: TestClient, db_session: Session) -> None:
    admin, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/users/{admin.id}/suspend",
        json={"reason": "Testing"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 403


def test_cannot_suspend_an_already_suspended_user(client: TestClient, db_session: Session) -> None:
    target, _ = _token(db_session, role="customer")
    _, admin_token = _token(db_session, role="administrator")

    client.post(
        f"/api/v1/admin/users/{target.id}/suspend",
        json={"reason": "First suspension"},
        headers=auth_headers(admin_token),
    )
    response = client.post(
        f"/api/v1/admin/users/{target.id}/suspend",
        json={"reason": "Second attempt"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 422


def test_admin_can_reactivate_a_suspended_user(client: TestClient, db_session: Session) -> None:
    target, _ = _token(db_session, role="customer")
    _, admin_token = _token(db_session, role="administrator")

    client.post(
        f"/api/v1/admin/users/{target.id}/suspend",
        json={"reason": "Investigating a report"},
        headers=auth_headers(admin_token),
    )
    response = client.post(
        f"/api/v1/admin/users/{target.id}/reactivate", headers=auth_headers(admin_token)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_search_filters_users_by_email(client: TestClient, db_session: Session) -> None:
    make_user(db_session, role="customer", email="findme@example.com")
    make_user(db_session, role="customer", email="someoneelse@example.com")
    _, admin_token = _token(db_session, role="administrator")

    response = client.get(
        "/api/v1/admin/users", params={"search": "findme"}, headers=auth_headers(admin_token)
    )

    assert response.status_code == 200
    emails = [u["email"] for u in response.json()["items"]]
    assert emails == ["findme@example.com"]


def test_invalid_sort_column_is_rejected(client: TestClient, db_session: Session) -> None:
    _, admin_token = _token(db_session, role="administrator")

    response = client.get(
        "/api/v1/admin/users", params={"sort_by": "password"}, headers=auth_headers(admin_token)
    )

    assert response.status_code == 422


def test_pagination_page_info_shape(client: TestClient, db_session: Session) -> None:
    for _ in range(3):
        make_user(db_session, role="customer")
    _, admin_token = _token(db_session, role="administrator")

    response = client.get(
        "/api/v1/admin/users", params={"page": 1, "page_size": 2}, headers=auth_headers(admin_token)
    )

    body = response.json()
    assert body["page_info"]["page"] == 1
    assert body["page_info"]["page_size"] == 2
    assert body["page_info"]["total"] >= 3
    assert len(body["items"]) == 2
