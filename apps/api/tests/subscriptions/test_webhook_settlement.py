"""Subscription payment settlement via the shared payments webhook — see
docs/subscriptions-and-entitlements.md#subscription-checkout-reuses-payments
and mirrors tests/payments/test_webhooks.py's structure."""

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.subscription import SubscriptionStatusHistory
from tests.db.factories import make_payment, make_subscription, make_subscription_plan, make_user


def _sign(body: bytes) -> str:
    secret = get_settings().razorpay_webhook_secret
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _payment_event(
    *, event: str, order_id: str, payment_id: str, amount: int, status: str
) -> bytes:
    error_description = "Insufficient funds." if event == "payment.failed" else None
    return json.dumps(
        {
            "entity": "event",
            "event": event,
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": order_id,
                        "amount": amount,
                        "currency": "INR",
                        "status": status,
                        "error_description": error_description,
                    }
                }
            },
        }
    ).encode()


def _post_webhook(client: TestClient, body: bytes):  # type: ignore[no-untyped-def]
    return client.post(
        "/api/v1/webhooks/payments/razorpay",
        content=body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": _sign(body)},
    )


def test_successful_payment_activates_a_trialing_subscription(
    client: TestClient, db_session: Session
) -> None:
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(db_session, target_role="customer", billing_interval="monthly")
    subscription = make_subscription(
        db_session,
        user=customer,
        plan=plan,
        status="trialing",
        current_period_start=datetime.now(UTC),
        current_period_end=datetime.now(UTC) + timedelta(days=30),
    )
    payment = make_payment(
        db_session,
        subscription=subscription,
        payer=customer,
        amount=19900,
        payment_type="subscription",
        status="pending",
    )
    db_session.commit()

    body = _payment_event(
        event="payment.captured",
        order_id=payment.provider_order_id,
        payment_id="pay_sub1",
        amount=19900,
        status="captured",
    )
    response = _post_webhook(client, body)
    assert response.status_code == 200

    db_session.refresh(subscription)
    assert subscription.status == "active"
    assert subscription.current_period_end > datetime.now(UTC)

    history = (
        db_session.execute(
            select(SubscriptionStatusHistory).where(
                SubscriptionStatusHistory.subscription_id == subscription.id
            )
        )
        .scalars()
        .all()
    )
    assert any(h.from_status == "trialing" and h.to_status == "active" for h in history)


def test_failed_first_payment_expires_the_trialing_subscription(
    client: TestClient, db_session: Session
) -> None:
    customer = make_user(db_session, role="customer")
    subscription = make_subscription(db_session, user=customer, status="trialing")
    payment = make_payment(
        db_session,
        subscription=subscription,
        payer=customer,
        amount=19900,
        payment_type="subscription",
        status="pending",
    )
    db_session.commit()

    body = _payment_event(
        event="payment.failed",
        order_id=payment.provider_order_id,
        payment_id="pay_sub2",
        amount=19900,
        status="failed",
    )
    response = _post_webhook(client, body)
    assert response.status_code == 200

    db_session.refresh(subscription)
    assert subscription.status == "expired"


def test_failed_renewal_payment_moves_an_active_subscription_to_past_due_with_grace_period(
    client: TestClient, db_session: Session
) -> None:
    customer = make_user(db_session, role="customer")
    subscription = make_subscription(db_session, user=customer, status="active")
    payment = make_payment(
        db_session,
        subscription=subscription,
        payer=customer,
        amount=19900,
        payment_type="subscription",
        status="pending",
    )
    db_session.commit()

    body = _payment_event(
        event="payment.failed",
        order_id=payment.provider_order_id,
        payment_id="pay_sub3",
        amount=19900,
        status="failed",
    )
    response = _post_webhook(client, body)
    assert response.status_code == 200

    db_session.refresh(subscription)
    assert subscription.status == "past_due"
    assert subscription.grace_period_ends_at is not None
    assert subscription.grace_period_ends_at > datetime.now(UTC)

    history = (
        db_session.execute(
            select(SubscriptionStatusHistory).where(
                SubscriptionStatusHistory.subscription_id == subscription.id
            )
        )
        .scalars()
        .all()
    )
    assert any(h.from_status == "active" and h.to_status == "past_due" for h in history)


def test_renewal_payment_success_clears_grace_period_and_extends_the_subscription(
    client: TestClient, db_session: Session
) -> None:
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(db_session, target_role="customer", billing_interval="monthly")
    old_period_end = datetime.now(UTC) + timedelta(days=1)
    subscription = make_subscription(
        db_session,
        user=customer,
        plan=plan,
        status="past_due",
        current_period_end=old_period_end,
        grace_period_ends_at=datetime.now(UTC) + timedelta(days=2),
    )
    payment = make_payment(
        db_session,
        subscription=subscription,
        payer=customer,
        amount=19900,
        payment_type="subscription",
        status="pending",
    )
    db_session.commit()

    body = _payment_event(
        event="payment.captured",
        order_id=payment.provider_order_id,
        payment_id="pay_sub4",
        amount=19900,
        status="captured",
    )
    response = _post_webhook(client, body)
    assert response.status_code == 200

    db_session.refresh(subscription)
    assert subscription.status == "active"
    assert subscription.grace_period_ends_at is None
    # Renewal chains from the old period end, not from "now".
    assert subscription.current_period_start == old_period_end


def test_amount_mismatch_fails_the_subscription_payment_without_activating(
    client: TestClient, db_session: Session
) -> None:
    customer = make_user(db_session, role="customer")
    subscription = make_subscription(db_session, user=customer, status="trialing")
    payment = make_payment(
        db_session,
        subscription=subscription,
        payer=customer,
        amount=19900,
        payment_type="subscription",
        status="pending",
    )
    db_session.commit()

    body = _payment_event(
        event="payment.captured",
        order_id=payment.provider_order_id,
        payment_id="pay_sub5",
        amount=1,
        status="captured",
    )
    response = _post_webhook(client, body)
    assert response.status_code == 200

    db_session.refresh(subscription)
    db_session.refresh(payment)
    assert subscription.status == "trialing"
    assert payment.status == "failed"
