"""Payment receipts — see docs/payments.md#3c-payment-receipts."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_artist_profile,
    make_artist_service,
    make_booking,
    make_payment,
    make_user,
)


def test_receipt_unavailable_for_a_pending_payment(client: TestClient, db_session: Session) -> None:
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

    response = client.get(
        f"/api/v1/bookings/{booking.id}/payments/{payment.id}/receipt", headers=auth_headers(token)
    )
    assert response.status_code == 422


def test_receipt_available_for_a_succeeded_payment(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    service = make_artist_service(db_session, artist_profile=profile, name="Bridal Henna")
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.DEPOSIT_PAID.value,
        deposit_amount=500.0,
        service_id=service.id,
    )
    payment = make_payment(
        db_session,
        booking=booking,
        payer=customer,
        amount=50000,
        status="succeeded",
        provider_payment_id="pay_receipt",
        commission_amount=7500,
        net_amount=42500,
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get(
        f"/api/v1/bookings/{booking.id}/payments/{payment.id}/receipt", headers=auth_headers(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == 50000
    assert body["service_name"] == "Bridal Henna"
    assert body["provider_payment_id"] == "pay_receipt"


def test_third_party_cannot_view_a_receipt(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    third_party = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.DEPOSIT_PAID.value,
        deposit_amount=500.0,
    )
    payment = make_payment(db_session, booking=booking, payer=customer, status="succeeded")
    db_session.commit()
    token = sign_token(third_party.id, email=third_party.email)

    response = client.get(
        f"/api/v1/bookings/{booking.id}/payments/{payment.id}/receipt", headers=auth_headers(token)
    )
    assert response.status_code == 403
