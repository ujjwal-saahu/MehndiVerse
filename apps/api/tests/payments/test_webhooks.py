"""Signed webhook handling — see
docs/payments.md#5-signed-webhook-handling-and-duplicate-protection and
#4-server-side-amount-validation."""

import hashlib
import hmac
import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.enums import BookingStatus
from app.db.models.booking import Booking
from app.db.models.payment import ArtistEarning
from app.db.models.system import AuditLog
from tests.db.factories import make_artist_profile, make_booking, make_payment, make_user


def _sign(body: bytes) -> str:
    secret = get_settings().razorpay_webhook_secret
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _payment_captured_payload(*, order_id: str, payment_id: str, amount: int) -> bytes:
    return json.dumps(
        {
            "entity": "event",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": order_id,
                        "amount": amount,
                        "currency": "INR",
                        "status": "captured",
                    }
                }
            },
        }
    ).encode()


def _payment_failed_payload(*, order_id: str, payment_id: str, amount: int) -> bytes:
    return json.dumps(
        {
            "entity": "event",
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": order_id,
                        "amount": amount,
                        "currency": "INR",
                        "status": "failed",
                        "error_description": "Insufficient funds in the account.",
                    }
                }
            },
        }
    ).encode()


def _post_webhook(client: TestClient, body: bytes, *, signature: str | None):  # type: ignore[no-untyped-def]
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Razorpay-Signature"] = signature
    return client.post("/api/v1/webhooks/payments/razorpay", content=body, headers=headers)


def test_valid_webhook_settles_the_payment_and_records_an_earning(
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
    payment = make_payment(
        db_session,
        booking=booking,
        payer=customer,
        amount=50000,
        payment_type="deposit",
        provider_order_id="order_abc",
    )
    db_session.commit()

    body = _payment_captured_payload(order_id="order_abc", payment_id="pay_abc", amount=50000)
    response = _post_webhook(client, body, signature=_sign(body))

    assert response.status_code == 200
    db_session.refresh(payment)
    assert payment.status == "succeeded"
    assert payment.provider_payment_id == "pay_abc"
    assert payment.commission_amount == 7500
    assert payment.net_amount == 42500

    booking_after = db_session.get(Booking, booking.id)
    assert booking_after is not None
    assert booking_after.status == BookingStatus.DEPOSIT_PAID.value

    earning = db_session.execute(
        select(ArtistEarning).where(ArtistEarning.payment_id == payment.id)
    ).scalar_one()
    assert earning.gross_amount == 50000
    assert earning.net_amount == 42500

    audit_actions = (
        db_session.execute(select(AuditLog.action).where(AuditLog.entity_id == payment.id))
        .scalars()
        .all()
    )
    assert "payment.succeeded" in audit_actions


def test_invalid_signature_is_rejected_and_payment_is_untouched(
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
    payment = make_payment(
        db_session,
        booking=booking,
        payer=customer,
        amount=50000,
        payment_type="deposit",
        provider_order_id="order_bad_sig",
    )
    db_session.commit()

    body = _payment_captured_payload(order_id="order_bad_sig", payment_id="pay_x", amount=50000)
    response = _post_webhook(client, body, signature="0" * 64)

    assert response.status_code == 400
    db_session.refresh(payment)
    assert payment.status == "pending"


def test_missing_signature_header_is_rejected(client: TestClient, db_session: Session) -> None:
    body = _payment_captured_payload(order_id="order_none", payment_id="pay_x", amount=50000)
    response = _post_webhook(client, body, signature=None)
    assert response.status_code == 400


def test_duplicate_webhook_delivery_is_only_processed_once(
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
    payment = make_payment(
        db_session,
        booking=booking,
        payer=customer,
        amount=50000,
        payment_type="deposit",
        provider_order_id="order_dup",
    )
    db_session.commit()

    body = _payment_captured_payload(order_id="order_dup", payment_id="pay_dup", amount=50000)
    signature = _sign(body)

    first = _post_webhook(client, body, signature=signature)
    second = _post_webhook(client, body, signature=signature)

    assert first.status_code == 200
    assert second.status_code == 200

    earning_count = (
        db_session.execute(select(ArtistEarning).where(ArtistEarning.payment_id == payment.id))
        .scalars()
        .all()
    )
    assert len(earning_count) == 1


def test_incorrect_amount_marks_the_payment_failed_instead_of_crediting_it(
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
    payment = make_payment(
        db_session,
        booking=booking,
        payer=customer,
        amount=50000,
        payment_type="deposit",
        provider_order_id="order_mismatch",
    )
    db_session.commit()

    # Provider reports a smaller amount than the order was actually created
    # for — must never be silently credited as if it were the full amount.
    body = _payment_captured_payload(order_id="order_mismatch", payment_id="pay_mismatch", amount=1)
    response = _post_webhook(client, body, signature=_sign(body))

    assert response.status_code == 200
    db_session.refresh(payment)
    assert payment.status == "failed"
    assert "mismatch" in (payment.failure_reason or "").lower()

    booking_after = db_session.get(Booking, booking.id)
    assert booking_after is not None
    assert booking_after.status == BookingStatus.DEPOSIT_PENDING.value  # unchanged

    earning = db_session.execute(
        select(ArtistEarning).where(ArtistEarning.payment_id == payment.id)
    ).scalar_one_or_none()
    assert earning is None


def test_failed_payment_webhook_marks_the_payment_failed(
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
    payment = make_payment(
        db_session,
        booking=booking,
        payer=customer,
        amount=50000,
        payment_type="deposit",
        provider_order_id="order_fail",
    )
    db_session.commit()

    body = _payment_failed_payload(order_id="order_fail", payment_id="pay_fail", amount=50000)
    response = _post_webhook(client, body, signature=_sign(body))

    assert response.status_code == 200
    db_session.refresh(payment)
    assert payment.status == "failed"
    assert payment.failure_reason == "Insufficient funds in the account."

    booking_after = db_session.get(Booking, booking.id)
    assert booking_after is not None
    assert booking_after.status == BookingStatus.DEPOSIT_PENDING.value  # unchanged
