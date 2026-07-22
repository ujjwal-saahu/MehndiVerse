"""Payment order creation is rate-limited — see docs/payments.md#5."""

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_artist_profile, make_booking, make_user


def test_payment_order_creation_is_rate_limited(
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
    razorpay_mock.post("/orders").mock(
        return_value=httpx.Response(
            200, json={"id": "order_rl", "amount": 50000, "currency": "INR", "status": "created"}
        )
    )

    statuses = [
        client.post(
            f"/api/v1/bookings/{booking.id}/payments",
            json={"payment_type": "deposit"},
            headers=auth_headers(token),
        ).status_code
        for _ in range(11)
    ]

    assert statuses[:10] == [201] * 10
    assert statuses[10] == 429
