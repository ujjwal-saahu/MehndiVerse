from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import PaymentStatus, RefundStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_payment, make_refund, make_user


def _token(db_session: Session, *, role: str):
    user = make_user(db_session, role=role)
    db_session.commit()
    return user, sign_token(user.id, email=user.email)


def test_list_payments_requires_staff(client: TestClient, db_session: Session) -> None:
    _, token = _token(db_session, role="customer")
    response = client.get("/api/v1/admin/payments", headers=auth_headers(token))
    assert response.status_code == 403


def test_moderator_can_view_payments(client: TestClient, db_session: Session) -> None:
    make_payment(db_session, status=PaymentStatus.SUCCEEDED.value)
    db_session.commit()
    _, moderator_token = _token(db_session, role="moderator")

    response = client.get("/api/v1/admin/payments", headers=auth_headers(moderator_token))

    assert response.status_code == 200
    assert response.json()["page_info"]["total"] >= 1


def test_filter_payments_by_status(client: TestClient, db_session: Session) -> None:
    succeeded = make_payment(db_session, status=PaymentStatus.SUCCEEDED.value)
    make_payment(db_session, status=PaymentStatus.PENDING.value)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.get(
        "/api/v1/admin/payments",
        params={"status_filter": "succeeded"},
        headers=auth_headers(admin_token),
    )

    ids = {p["id"] for p in response.json()["items"]}
    assert str(succeeded.id) in ids


def test_list_refunds_requires_staff(client: TestClient, db_session: Session) -> None:
    _, token = _token(db_session, role="customer")
    response = client.get("/api/v1/admin/payments/refunds", headers=auth_headers(token))
    assert response.status_code == 403


def test_admin_can_list_pending_refunds(client: TestClient, db_session: Session) -> None:
    payment = make_payment(db_session, status=PaymentStatus.SUCCEEDED.value)
    refund = make_refund(db_session, payment=payment, status=RefundStatus.PENDING.value)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.get(
        "/api/v1/admin/payments/refunds",
        params={"status_filter": "pending"},
        headers=auth_headers(admin_token),
    )

    ids = {r["id"] for r in response.json()["items"]}
    assert str(refund.id) in ids


def test_reject_refund_requires_a_reason(client: TestClient, db_session: Session) -> None:
    payment = make_payment(db_session, status=PaymentStatus.SUCCEEDED.value)
    refund = make_refund(db_session, payment=payment, status=RefundStatus.PENDING.value)
    db_session.commit()
    _, admin_token = _token(db_session, role="administrator")

    response = client.post(
        f"/api/v1/admin/payments/refunds/{refund.id}/reject",
        json={"reason": ""},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 422


def test_moderator_cannot_reject_a_refund(client: TestClient, db_session: Session) -> None:
    payment = make_payment(db_session, status=PaymentStatus.SUCCEEDED.value)
    refund = make_refund(db_session, payment=payment, status=RefundStatus.PENDING.value)
    db_session.commit()
    _, moderator_token = _token(db_session, role="moderator")

    response = client.post(
        f"/api/v1/admin/payments/refunds/{refund.id}/reject",
        json={"reason": "Outside policy window"},
        headers=auth_headers(moderator_token),
    )

    assert response.status_code == 403
