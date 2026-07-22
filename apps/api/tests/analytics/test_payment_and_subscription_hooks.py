"""Verifies the `payment_completed`/`subscription_started`/`ai_generation_
requested` event hooks — see docs/analytics-and-recommendations.md#track-
events-for. `payment_completed` is exercised through the real signed-
webhook flow (mirrors tests/payments/test_webhooks.py); the others call
their owning service function directly."""

import hashlib
import hmac
import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.enums import AnalyticsEventType, BookingStatus, SubscriptionStatus
from app.db.models.analytics import AnalyticsEvent
from app.services.ai.generations import create_ai_generation
from app.services.subscriptions import activate_or_renew_subscription
from tests.db.factories import (
    make_artist_profile,
    make_booking,
    make_consenting_user,
    make_payment,
    make_subscription,
    make_subscription_plan,
)


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


def test_settled_booking_payment_records_payment_completed(
    client: TestClient, db_session: Session
) -> None:
    profile = make_artist_profile(db_session)
    customer = make_consenting_user(db_session)
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
        provider_order_id="order_abc123",
    )
    db_session.commit()

    body = _payment_captured_payload(order_id="order_abc123", payment_id="pay_xyz", amount=50000)
    response = client.post(
        "/api/v1/webhooks/payments/razorpay",
        content=body,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": _sign(body)},
    )
    assert response.status_code == 200

    events = (
        db_session.execute(
            select(AnalyticsEvent).where(
                AnalyticsEvent.event_type == AnalyticsEventType.PAYMENT_COMPLETED.value,
                AnalyticsEvent.entity_id == payment.id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1


def test_first_subscription_activation_records_subscription_started(
    db_session: Session,
) -> None:
    user = make_consenting_user(db_session)
    plan = make_subscription_plan(db_session)
    subscription = make_subscription(
        db_session, user=user, plan=plan, status=SubscriptionStatus.TRIALING.value
    )
    payment = make_payment(db_session, subscription=subscription, payer=user, amount=19900)
    db_session.commit()

    activate_or_renew_subscription(db_session, payment)
    db_session.commit()

    events = (
        db_session.execute(
            select(AnalyticsEvent).where(
                AnalyticsEvent.event_type == AnalyticsEventType.SUBSCRIPTION_STARTED.value,
                AnalyticsEvent.entity_id == subscription.id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1


def test_subscription_renewal_does_not_record_subscription_started_again(
    db_session: Session,
) -> None:
    user = make_consenting_user(db_session)
    plan = make_subscription_plan(db_session)
    subscription = make_subscription(
        db_session, user=user, plan=plan, status=SubscriptionStatus.ACTIVE.value
    )
    payment = make_payment(db_session, subscription=subscription, payer=user, amount=19900)
    db_session.commit()

    activate_or_renew_subscription(db_session, payment)
    db_session.commit()

    events = (
        db_session.execute(
            select(AnalyticsEvent).where(
                AnalyticsEvent.event_type == AnalyticsEventType.SUBSCRIPTION_STARTED.value,
                AnalyticsEvent.entity_id == subscription.id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 0


def test_create_ai_generation_records_ai_generation_requested(db_session: Session) -> None:
    user = make_consenting_user(db_session)
    db_session.commit()

    generation = create_ai_generation(
        db_session,
        user=user,
        generation_type="design_discovery",
        request_payload={"query": "bridal"},
    )
    db_session.commit()

    events = (
        db_session.execute(
            select(AnalyticsEvent).where(
                AnalyticsEvent.event_type == AnalyticsEventType.AI_GENERATION_REQUESTED.value,
                AnalyticsEvent.entity_id == generation.id,
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
