"""Refund request/approval and the confirming webhook — see
docs/payments.md#6-refunds."""

import hashlib
import hmac
import json

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.enums import BookingStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_booking, make_payment, make_user


def _sign(body: bytes) -> str:
    secret = get_settings().razorpay_webhook_secret
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _setup_succeeded_payment(db_session: Session):  # type: ignore[no-untyped-def]
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.DEPOSIT_PAID.value,
        deposit_amount=500.0,
    )
    payment = make_payment(
        db_session,
        booking=booking,
        payer=customer,
        amount=50000,
        payment_type="deposit",
        status="succeeded",
        provider_payment_id="pay_refundme",
        commission_amount=7500,
        net_amount=42500,
    )
    db_session.commit()
    return profile, customer, booking, payment


def test_customer_can_request_a_refund(client: TestClient, db_session: Session) -> None:
    profile, customer, booking, payment = _setup_succeeded_payment(db_session)
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/payments/{payment.id}/refund",
        json={"reason": "Customer changed their mind."},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["amount"] == 50000


def test_third_party_cannot_request_a_refund(client: TestClient, db_session: Session) -> None:
    profile, customer, booking, payment = _setup_succeeded_payment(db_session)
    third_party = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(third_party.id, email=third_party.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/payments/{payment.id}/refund",
        json={},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_cannot_refund_a_pending_payment(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.DEPOSIT_PENDING.value,
        deposit_amount=500.0,
    )
    payment = make_payment(db_session, booking=booking, payer=customer, status="pending")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/payments/{payment.id}/refund",
        json={},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_cannot_request_a_second_refund_while_one_is_open(
    client: TestClient, db_session: Session
) -> None:
    profile, customer, booking, payment = _setup_succeeded_payment(db_session)
    token = sign_token(customer.id, email=customer.email)
    client.post(
        f"/api/v1/bookings/{booking.id}/payments/{payment.id}/refund",
        json={},
        headers=auth_headers(token),
    )

    response = client.post(
        f"/api/v1/bookings/{booking.id}/payments/{payment.id}/refund",
        json={},
        headers=auth_headers(token),
    )
    assert response.status_code == 409


def test_non_staff_cannot_approve_a_refund(client: TestClient, db_session: Session) -> None:
    profile, customer, booking, payment = _setup_succeeded_payment(db_session)
    token = sign_token(customer.id, email=customer.email)
    refund = client.post(
        f"/api/v1/bookings/{booking.id}/payments/{payment.id}/refund",
        json={},
        headers=auth_headers(token),
    ).json()

    response = client.post(
        f"/api/v1/admin/payments/refunds/{refund['id']}/approve", headers=auth_headers(token)
    )
    assert response.status_code == 403


def test_staff_can_approve_a_refund(client: TestClient, db_session: Session, razorpay_mock) -> None:
    profile, customer, booking, payment = _setup_succeeded_payment(db_session)
    customer_token = sign_token(customer.id, email=customer.email)
    refund = client.post(
        f"/api/v1/bookings/{booking.id}/payments/{payment.id}/refund",
        json={"reason": "not happy"},
        headers=auth_headers(customer_token),
    ).json()

    admin = make_user(db_session, role="administrator")
    db_session.commit()
    admin_token = sign_token(admin.id, email=admin.email)
    razorpay_mock.post(f"/payments/{payment.provider_payment_id}/refund").mock(
        return_value=httpx.Response(
            200, json={"id": "rfnd_1", "entity": "refund", "amount": 50000, "status": "processed"}
        )
    )

    response = client.post(
        f"/api/v1/admin/payments/refunds/{refund['id']}/approve", headers=auth_headers(admin_token)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_staff_can_reject_a_refund(client: TestClient, db_session: Session) -> None:
    profile, customer, booking, payment = _setup_succeeded_payment(db_session)
    customer_token = sign_token(customer.id, email=customer.email)
    refund = client.post(
        f"/api/v1/bookings/{booking.id}/payments/{payment.id}/refund",
        json={},
        headers=auth_headers(customer_token),
    ).json()

    admin = make_user(db_session, role="administrator")
    db_session.commit()
    admin_token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/payments/refunds/{refund['id']}/reject",
        json={"reason": "Outside the refund window."},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_refund_processed_webhook_marks_payment_refunded(
    client: TestClient, db_session: Session, razorpay_mock
) -> None:
    profile, customer, booking, payment = _setup_succeeded_payment(db_session)
    customer_token = sign_token(customer.id, email=customer.email)
    refund = client.post(
        f"/api/v1/bookings/{booking.id}/payments/{payment.id}/refund",
        json={},
        headers=auth_headers(customer_token),
    ).json()

    admin = make_user(db_session, role="administrator")
    db_session.commit()
    admin_token = sign_token(admin.id, email=admin.email)
    razorpay_mock.post(f"/payments/{payment.provider_payment_id}/refund").mock(
        return_value=httpx.Response(
            200,
            json={"id": "rfnd_webhook", "entity": "refund", "amount": 50000, "status": "created"},
        )
    )
    client.post(
        f"/api/v1/admin/payments/refunds/{refund['id']}/approve", headers=auth_headers(admin_token)
    )

    body = json.dumps(
        {
            "entity": "event",
            "event": "refund.processed",
            "payload": {
                "refund": {
                    "entity": {
                        "id": "rfnd_webhook",
                        "payment_id": payment.provider_payment_id,
                        "amount": 50000,
                        "currency": "INR",
                        "status": "processed",
                    }
                }
            },
        }
    ).encode()
    response = client.post(
        "/api/v1/webhooks/payments/razorpay",
        content=body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": _sign(body)},
    )

    assert response.status_code == 200
    db_session.refresh(payment)
    assert payment.status == "refunded"
