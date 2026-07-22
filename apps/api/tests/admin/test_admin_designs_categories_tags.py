import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import DesignStatus
from app.db.models.system import AuditLog
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_category, make_design, make_user


def _token(db_session: Session, *, role: str):
    user = make_user(db_session, role=role)
    db_session.commit()
    return user, sign_token(user.id, email=user.email)


# --- Design moderation ------------------------------------------------------


def test_list_designs_requires_staff(client: TestClient, db_session: Session) -> None:
    _, token = _token(db_session, role="customer")
    response = client.get("/api/v1/admin/designs", headers=auth_headers(token))
    assert response.status_code == 403


def test_moderator_can_list_designs_but_not_moderate(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status=DesignStatus.PUBLISHED.value)
    db_session.commit()
    _, moderator_token = _token(db_session, role="moderator")

    list_response = client.get("/api/v1/admin/designs", headers=auth_headers(moderator_token))
    assert list_response.status_code == 200

    moderate_response = client.post(
        f"/api/v1/admin/designs/{design.id}/moderate",
        json={"action": "flag", "reason": "Reported for copyright infringement"},
        headers=auth_headers(moderator_token),
    )
    assert moderate_response.status_code == 403


def test_admin_can_flag_a_design_with_reason(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status=DesignStatus.PUBLISHED.value)
    db_session.commit()
    admin, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/designs/{design.id}/moderate",
        json={"action": "flag", "reason": "Reported for copyright infringement"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "flagged"

    entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_type == "designs", AuditLog.entity_id == design.id)
        .one()
    )
    assert entry.action == "design.moderate.flag"
    assert entry.actor_id == admin.id


def test_moderate_without_reason_is_rejected(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status=DesignStatus.PUBLISHED.value)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/designs/{design.id}/moderate",
        json={"action": "flag", "reason": ""},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 422


def test_moderate_unknown_action_is_rejected(client: TestClient, db_session: Session) -> None:
    design = make_design(db_session, status=DesignStatus.PUBLISHED.value)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/designs/{design.id}/moderate",
        json={"action": "delete_forever", "reason": "test"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 422


# --- Category management ------------------------------------------------------


def test_category_search_and_include_inactive_requires_staff(
    client: TestClient, db_session: Session
) -> None:
    make_category(db_session, name=f"Bridal-{uuid.uuid4().hex[:8]}")
    db_session.commit()
    _, customer_token = _token(db_session, role="customer")

    response = client.get(
        "/api/v1/categories",
        params={"include_inactive": "true"},
        headers=auth_headers(customer_token),
    )

    assert response.status_code == 403


def test_category_search_filters_by_name(client: TestClient, db_session: Session) -> None:
    unique = uuid.uuid4().hex[:8]
    make_category(db_session, name=f"Zzyx-Bridal-Mehndi-{unique}")
    make_category(db_session, name=f"Zzyx-Party-Glitter-{unique}")
    db_session.commit()
    _, token = _token(db_session, role="customer")

    response = client.get(
        "/api/v1/categories",
        params={"search": f"bridal-mehndi-{unique}"},
        headers=auth_headers(token),
    )

    names = [c["name"] for c in response.json()]
    assert names == [f"Zzyx-Bridal-Mehndi-{unique}"]


def test_moderator_cannot_delete_category(client: TestClient, db_session: Session) -> None:
    category = make_category(db_session)
    db_session.commit()
    _, moderator_token = _token(db_session, role="moderator")

    response = client.delete(
        f"/api/v1/categories/{category.id}", headers=auth_headers(moderator_token)
    )

    assert response.status_code == 403


def test_admin_can_delete_a_category(client: TestClient, db_session: Session) -> None:
    category = make_category(db_session)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.delete(f"/api/v1/categories/{category.id}", headers=auth_headers(admin_token))
    assert response.status_code == 204

    list_response = client.get("/api/v1/categories", headers=auth_headers(admin_token))
    ids = [c["id"] for c in list_response.json()]
    assert str(category.id) not in ids


# --- Tag management ------------------------------------------------------


def test_tag_crud_requires_edit_role_for_mutations(client: TestClient, db_session: Session) -> None:
    _, moderator_token = _token(db_session, role="moderator")

    response = client.post(
        "/api/v1/admin/tags",
        json={"name": "floral", "slug": "floral"},
        headers=auth_headers(moderator_token),
    )

    assert response.status_code == 403


def test_admin_can_create_list_and_delete_a_tag(client: TestClient, db_session: Session) -> None:
    _, admin_token = _token(db_session, role="administrator")

    create_response = client.post(
        "/api/v1/admin/tags",
        json={"name": "floral", "slug": "floral"},
        headers=auth_headers(admin_token),
    )
    assert create_response.status_code == 201
    tag_id = create_response.json()["id"]

    list_response = client.get(
        "/api/v1/admin/tags", params={"search": "flor"}, headers=auth_headers(admin_token)
    )
    assert any(t["id"] == tag_id for t in list_response.json()["items"])

    delete_response = client.delete(
        f"/api/v1/admin/tags/{tag_id}", headers=auth_headers(admin_token)
    )
    assert delete_response.status_code == 204


def test_duplicate_tag_name_is_rejected(client: TestClient, db_session: Session) -> None:
    _, admin_token = _token(db_session, role="administrator")
    client.post(
        "/api/v1/admin/tags",
        json={"name": "floral", "slug": "floral"},
        headers=auth_headers(admin_token),
    )

    response = client.post(
        "/api/v1/admin/tags",
        json={"name": "floral", "slug": "floral-2"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 409
