from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import DesignStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_comment, make_design, make_report, make_user


def _pending_design_report(db_session: Session):
    design = make_design(db_session, status=DesignStatus.PUBLISHED.value)
    reporter = make_user(db_session, role="customer")
    report = make_report(db_session, reporter=reporter, entity_type="design", entity_id=design.id)
    db_session.commit()
    return design, reporter, report


def test_queue_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/admin/reports")
    assert response.status_code == 401


def test_queue_requires_staff_role(client: TestClient, db_session: Session) -> None:
    _pending_design_report(db_session)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get("/api/v1/admin/reports", headers=auth_headers(token))

    assert response.status_code == 403


def test_moderator_can_view_queue(client: TestClient, db_session: Session) -> None:
    _, _, report = _pending_design_report(db_session)
    moderator = make_user(db_session, role="moderator")
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get("/api/v1/admin/reports", headers=auth_headers(token))

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(report.id)]


def test_queue_rejects_an_unknown_status_filter(client: TestClient, db_session: Session) -> None:
    moderator = make_user(db_session, role="moderator")
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get(
        "/api/v1/admin/reports?status_filter=not_a_real_status", headers=auth_headers(token)
    )

    assert response.status_code == 422


def test_queue_defaults_to_pending_only(client: TestClient, db_session: Session) -> None:
    _, _, pending_report = _pending_design_report(db_session)
    design = make_design(db_session, status=DesignStatus.PUBLISHED.value)
    reporter = make_user(db_session, role="customer")
    resolved_report = make_report(
        db_session,
        reporter=reporter,
        entity_type="design",
        entity_id=design.id,
        status="resolved",
    )
    db_session.commit()
    moderator = make_user(db_session, role="moderator")
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.get("/api/v1/admin/reports", headers=auth_headers(token))

    ids = {item["id"] for item in response.json()["items"]}
    assert ids == {str(pending_report.id)}
    assert str(resolved_report.id) not in ids


def test_queue_entity_snapshot_survives_comment_soft_delete(
    client: TestClient, db_session: Session
) -> None:
    design = make_design(db_session, status=DesignStatus.PUBLISHED.value)
    author = make_user(db_session, role="customer")
    comment = make_comment(db_session, design=design, user=author, body="Nasty comment")
    reporter = make_user(db_session, role="customer")
    report = make_report(db_session, reporter=reporter, entity_type="comment", entity_id=comment.id)
    db_session.commit()

    # Author deletes the comment (soft-delete) after being reported.
    author_token = sign_token(author.id, email=author.email)
    delete_response = client.delete(
        f"/api/v1/comments/{comment.id}", headers=auth_headers(author_token)
    )
    assert delete_response.status_code == 204

    moderator = make_user(db_session, role="moderator")
    db_session.commit()
    mod_token = sign_token(moderator.id, email=moderator.email)

    response = client.get(f"/api/v1/admin/reports/{report.id}", headers=auth_headers(mod_token))

    assert response.status_code == 200
    snapshot = response.json()["entity_snapshot"]
    assert snapshot["body"] == "Nasty comment"
    assert snapshot["is_deleted"] is True


def test_moderator_cannot_resolve_report(client: TestClient, db_session: Session) -> None:
    _, _, report = _pending_design_report(db_session)
    moderator = make_user(db_session, role="moderator")
    db_session.commit()
    token = sign_token(moderator.id, email=moderator.email)

    response = client.post(
        f"/api/v1/admin/reports/{report.id}/resolve",
        json={"resolution_notes": "Looked into it"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_admin_can_resolve_report(client: TestClient, db_session: Session) -> None:
    _, _, report = _pending_design_report(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/reports/{report.id}/resolve",
        json={"resolution_notes": "Confirmed and actioned separately"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["resolved_by"] == str(admin.id)


def test_admin_can_dismiss_report(client: TestClient, db_session: Session) -> None:
    _, _, report = _pending_design_report(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/reports/{report.id}/dismiss",
        json={"resolution_notes": "Not a violation"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "dismissed"


def test_cannot_resolve_an_already_closed_report(client: TestClient, db_session: Session) -> None:
    _, _, report = _pending_design_report(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    client.post(
        f"/api/v1/admin/reports/{report.id}/dismiss",
        json={"resolution_notes": "Not a violation"},
        headers=auth_headers(token),
    )

    response = client.post(
        f"/api/v1/admin/reports/{report.id}/resolve",
        json={"resolution_notes": "Too late"},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_resolving_a_report_without_notes_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    _, _, report = _pending_design_report(db_session)
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/reports/{report.id}/resolve",
        json={"resolution_notes": ""},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
