from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.system import AuditLog
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_user


def _token(db_session: Session, *, role: str):
    user = make_user(db_session, role=role)
    db_session.commit()
    return user, sign_token(user.id, email=user.email)


# --- Global audit-log viewer ------------------------------------------------------


def test_moderator_cannot_view_the_global_audit_log(
    client: TestClient, db_session: Session
) -> None:
    _, moderator_token = _token(db_session, role="moderator")

    response = client.get("/api/v1/admin/audit-logs", headers=auth_headers(moderator_token))

    assert response.status_code == 403


def test_admin_can_view_the_global_audit_log_and_see_a_privileged_change(
    client: TestClient, db_session: Session
) -> None:
    target, _ = _token(db_session, role="customer")
    _, admin_token = _token(db_session, role="administrator")

    client.post(
        f"/api/v1/admin/users/{target.id}/suspend",
        json={"reason": "Testing audit trail visibility"},
        headers=auth_headers(admin_token),
    )

    response = client.get(
        "/api/v1/admin/audit-logs",
        params={"entity_type": "users", "action": "user.suspend"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    entity_ids = {entry["entity_id"] for entry in response.json()["items"]}
    assert str(target.id) in entity_ids


# --- System settings (super-admin only) ------------------------------------------------------


def test_admin_cannot_view_system_settings(client: TestClient, db_session: Session) -> None:
    _, admin_token = _token(db_session, role="administrator")

    response = client.get("/api/v1/admin/settings", headers=auth_headers(admin_token))

    assert response.status_code == 403


def test_super_admin_can_read_and_write_a_system_setting(
    client: TestClient, db_session: Session
) -> None:
    _, super_admin_token = _token(db_session, role="super_administrator")

    write_response = client.put(
        "/api/v1/admin/settings/maintenance_mode",
        json={"value": {"enabled": False}, "description": "Site-wide maintenance toggle"},
        headers=auth_headers(super_admin_token),
    )
    assert write_response.status_code == 200
    assert write_response.json()["key"] == "maintenance_mode"

    list_response = client.get("/api/v1/admin/settings", headers=auth_headers(super_admin_token))
    keys = [s["key"] for s in list_response.json()["items"]]
    assert "maintenance_mode" in keys


def test_updating_a_system_setting_is_audited(client: TestClient, db_session: Session) -> None:
    super_admin, super_admin_token = _token(db_session, role="super_administrator")

    client.put(
        "/api/v1/admin/settings/maintenance_mode",
        json={"value": {"enabled": True}},
        headers=auth_headers(super_admin_token),
    )

    entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "system_settings")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert entry is not None
    assert entry.actor_id == super_admin.id
    assert entry.action == "system_setting.upsert"


# --- Dashboard overview ------------------------------------------------------


def test_dashboard_overview_requires_staff(client: TestClient, db_session: Session) -> None:
    _, token = _token(db_session, role="customer")

    response = client.get("/api/v1/admin/dashboard/overview", headers=auth_headers(token))

    assert response.status_code == 403


def test_moderator_can_view_dashboard_overview(client: TestClient, db_session: Session) -> None:
    _, moderator_token = _token(db_session, role="moderator")

    response = client.get("/api/v1/admin/dashboard/overview", headers=auth_headers(moderator_token))

    assert response.status_code == 200
    body = response.json()
    for key in (
        "pending_artist_verifications",
        "pending_reports",
        "pending_refunds",
        "disputed_bookings",
        "total_users",
        "total_artists",
        "total_designs",
        "total_bookings",
    ):
        assert key in body
