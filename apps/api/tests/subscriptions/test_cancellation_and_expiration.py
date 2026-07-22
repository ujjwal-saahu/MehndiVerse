"""Cancellation, expiration, and the grace-period foundation function — see
docs/subscriptions-and-entitlements.md#grace-period and
docs/subscriptions-and-entitlements.md#cancellation."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.subscription import SubscriptionStatusHistory
from app.db.models.system import AuditLog
from app.services.subscriptions import process_due_subscriptions
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_subscription, make_user


def test_cancel_requires_ownership(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    other = make_user(db_session, role="customer")
    make_subscription(db_session, user=customer, status="active")
    db_session.commit()
    token = sign_token(other.id, email=other.email)

    response = client.post("/api/v1/subscriptions/me/cancel", json={}, headers=auth_headers(token))
    assert response.status_code == 404  # `other` has no subscription of their own


def test_cancel_sets_cancel_at_period_end_without_revoking_access(
    client: TestClient, db_session: Session
) -> None:
    customer = make_user(db_session, role="customer")
    make_subscription(db_session, user=customer, status="active")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/subscriptions/me/cancel",
        json={"reason": "Too expensive"},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cancel_at_period_end"] is True
    assert body["status"] == "active"  # Access continues through the paid period.

    audit = (
        db_session.execute(select(AuditLog).where(AuditLog.action == "subscription.cancelled"))
        .scalars()
        .first()
    )
    assert audit is not None
    assert audit.after_state["reason"] == "Too expensive"


def test_cancelled_subscription_expires_once_its_period_ends(db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    subscription = make_subscription(
        db_session,
        user=customer,
        status="active",
        cancel_at_period_end=True,
        current_period_start=datetime.now(UTC) - timedelta(days=30),
        current_period_end=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.commit()

    changed = process_due_subscriptions(db_session)
    db_session.commit()

    assert changed == 1
    db_session.refresh(subscription)
    assert subscription.status == "expired"


def test_non_cancelled_subscription_enters_grace_period_at_period_end(db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    subscription = make_subscription(
        db_session,
        user=customer,
        status="active",
        cancel_at_period_end=False,
        current_period_start=datetime.now(UTC) - timedelta(days=30),
        current_period_end=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.commit()

    process_due_subscriptions(db_session)
    db_session.commit()

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
    assert any(h.to_status == "past_due" for h in history)


def test_past_due_subscription_expires_once_grace_period_elapses(db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    subscription = make_subscription(
        db_session,
        user=customer,
        status="past_due",
        grace_period_ends_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.commit()

    changed = process_due_subscriptions(db_session)
    db_session.commit()

    assert changed == 1
    db_session.refresh(subscription)
    assert subscription.status == "expired"


def test_past_due_subscription_within_grace_period_is_left_alone(db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    subscription = make_subscription(
        db_session,
        user=customer,
        status="past_due",
        grace_period_ends_at=datetime.now(UTC) + timedelta(days=1),
    )
    db_session.commit()

    changed = process_due_subscriptions(db_session)

    assert changed == 0
    db_session.refresh(subscription)
    assert subscription.status == "past_due"


def test_active_subscription_not_yet_at_period_end_is_untouched(db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    subscription = make_subscription(
        db_session,
        user=customer,
        status="active",
        current_period_end=datetime.now(UTC) + timedelta(days=10),
    )
    db_session.commit()

    changed = process_due_subscriptions(db_session)

    assert changed == 0
    db_session.refresh(subscription)
    assert subscription.status == "active"
