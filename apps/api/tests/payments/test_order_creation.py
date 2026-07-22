"""Payment order creation — see docs/payments.md#3-payment-order-creation
and #4-server-side-amount-validation and #6-idempotency-keys."""

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_booking, make_payment, make_user

_ORDER_RESPONSE = {
    "id": "order_test123",
    "entity": "order",
    "amount": 50000,
    "amount_paid": 0,
    "amount_due": 50000,
    "currency": "INR",
    "status": "created",
}


def _mock_order_creation(razorpay_mock, response: dict | None = None):  # type: ignore[no-untyped-def]
    return razorpay_mock.post("/orders").mock(
        return_value=httpx.Response(200, json=response or _ORDER_RESPONSE)
    )


def test_create_order_requires_authentication(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    booking = make_booking(
        db_session,
        artist_profile=profile,
        status=BookingStatus.DEPOSIT_PENDING.value,
        deposit_amount=500.0,
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/bookings/{booking.id}/payments", json={"payment_type": "deposit"}
    )
    assert response.status_code == 401


def test_third_party_cannot_create_an_order(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    booking = make_booking(
        db_session,
        artist_profile=profile,
        status=BookingStatus.DEPOSIT_PENDING.value,
        deposit_amount=500.0,
    )
    third_party = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(third_party.id, email=third_party.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/payments",
        json={"payment_type": "deposit"},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_create_deposit_order_succeeds(
    client: TestClient, db_session: Session, razorpay_mock
) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.DEPOSIT_PENDING.value,
        deposit_amount=500.0,
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    route = _mock_order_creation(razorpay_mock)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/payments",
        json={"payment_type": "deposit"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == 50000
    assert body["currency"] == "INR"
    assert body["provider_order_id"] == "order_test123"
    assert body["provider_key_id"]
    assert route.call_count == 1


def test_order_amount_is_server_determined_not_client_supplied(
    client: TestClient, db_session: Session, razorpay_mock
) -> None:
    """The request schema has no amount field at all, but even so, extra
    JSON keys a client might smuggle in are simply ignored — the amount
    always comes from the booking's own stored deposit_amount."""
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.DEPOSIT_PENDING.value,
        deposit_amount=500.0,
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    _mock_order_creation(razorpay_mock)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/payments",
        json={"payment_type": "deposit", "amount": 1, "amount_minor": 1},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["amount"] == 50000


def test_full_payment_requires_confirmed_status(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.REQUESTED.value,
        total_amount=1000.0,
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/payments",
        json={"payment_type": "full"},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_idempotency_key_reuses_the_same_order(
    client: TestClient, db_session: Session, razorpay_mock
) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.DEPOSIT_PENDING.value,
        deposit_amount=500.0,
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    route = _mock_order_creation(razorpay_mock)

    first = client.post(
        f"/api/v1/bookings/{booking.id}/payments",
        json={"payment_type": "deposit", "idempotency_key": "key-123"},
        headers=auth_headers(token),
    ).json()
    second = client.post(
        f"/api/v1/bookings/{booking.id}/payments",
        json={"payment_type": "deposit", "idempotency_key": "key-123"},
        headers=auth_headers(token),
    ).json()

    assert first["payment_id"] == second["payment_id"]
    assert route.call_count == 1


def test_repeated_request_without_idempotency_key_reuses_the_pending_order(
    client: TestClient, db_session: Session, razorpay_mock
) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.DEPOSIT_PENDING.value,
        deposit_amount=500.0,
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    route = _mock_order_creation(razorpay_mock)

    first = client.post(
        f"/api/v1/bookings/{booking.id}/payments",
        json={"payment_type": "deposit"},
        headers=auth_headers(token),
    ).json()
    second = client.post(
        f"/api/v1/bookings/{booking.id}/payments",
        json={"payment_type": "deposit"},
        headers=auth_headers(token),
    ).json()

    assert first["payment_id"] == second["payment_id"]
    assert route.call_count == 1


def test_cannot_create_order_for_an_already_paid_type(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    customer = make_user(db_session, role="customer")
    booking = make_booking(
        db_session,
        customer=customer,
        artist_profile=profile,
        status=BookingStatus.DEPOSIT_PENDING.value,
        deposit_amount=500.0,
    )
    make_payment(
        db_session,
        booking=booking,
        payer=customer,
        payment_type="deposit",
        status="succeeded",
        amount=50000,
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        f"/api/v1/bookings/{booking.id}/payments",
        json={"payment_type": "deposit"},
        headers=auth_headers(token),
    )
    assert response.status_code == 409
