"""GET /account/data-export — see docs/legal-and-support.md#data-export-
request."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.support import DataExportRequest
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_booking, make_payment, make_user


def test_data_export_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/account/data-export")
    assert response.status_code == 401


def test_data_export_includes_the_caller_s_own_bookings_and_payments(
    client: TestClient, db_session: Session
) -> None:
    customer = make_user(db_session)
    booking = make_booking(db_session, customer=customer)
    make_payment(db_session, booking=booking, payer=customer)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get("/api/v1/account/data-export", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["email"] == customer.email
    assert len(body["bookings"]) == 1
    assert body["bookings"][0]["id"] == str(booking.id)
    assert len(body["payments"]) == 1


def test_data_export_excludes_another_user_s_bookings(
    client: TestClient, db_session: Session
) -> None:
    customer = make_user(db_session)
    other_customer = make_user(db_session)
    make_booking(db_session, customer=other_customer)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get("/api/v1/account/data-export", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["bookings"] == []


def test_data_export_logs_an_audit_row(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    client.get("/api/v1/account/data-export", headers=auth_headers(token))

    rows = (
        db_session.query(DataExportRequest).filter(DataExportRequest.user_id == customer.id).all()
    )
    assert len(rows) >= 1
