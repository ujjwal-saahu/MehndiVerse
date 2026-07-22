"""GET /subscriptions/me/billing-history and GET /subscriptions/{id}/status-
history — uncovered before Phase 26 (coverage audit)."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import PaymentStatus, PaymentType, SubscriptionStatus
from app.services.subscriptions import activate_or_renew_subscription
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_payment, make_subscription, make_subscription_plan, make_user


def test_billing_history_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/subscriptions/me/billing-history")
    assert response.status_code == 401


def test_billing_history_returns_only_the_caller_s_subscription_payments(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    plan = make_subscription_plan(db_session)
    subscription = make_subscription(db_session, user=user, plan=plan)
    make_payment(
        db_session,
        subscription=subscription,
        payer=user,
        amount=19900,
        payment_type=PaymentType.SUBSCRIPTION.value,
        status=PaymentStatus.SUCCEEDED.value,
    )
    # A different user's subscription payment must never appear.
    other_user = make_user(db_session)
    other_subscription = make_subscription(db_session, user=other_user, plan=plan)
    make_payment(
        db_session,
        subscription=other_subscription,
        payer=other_user,
        payment_type=PaymentType.SUBSCRIPTION.value,
    )
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get("/api/v1/subscriptions/me/billing-history", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["plan_name"] == plan.name
    assert body[0]["amount"] == 19900


def test_status_history_requires_authentication(client: TestClient) -> None:
    response = client.get(f"/api/v1/subscriptions/{uuid.uuid4()}/status-history")
    assert response.status_code == 401


def test_status_history_returns_403_for_a_subscription_owned_by_someone_else(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session)
    subscription = make_subscription(db_session, user=owner)
    stranger = make_user(db_session)
    db_session.commit()
    token = sign_token(stranger.id, email=stranger.email)

    response = client.get(
        f"/api/v1/subscriptions/{subscription.id}/status-history", headers=auth_headers(token)
    )

    assert response.status_code == 403


def test_status_history_returns_404_for_a_nonexistent_subscription(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get(
        f"/api/v1/subscriptions/{uuid.uuid4()}/status-history", headers=auth_headers(token)
    )

    assert response.status_code == 404


def test_owner_sees_their_subscription_s_status_history(
    client: TestClient, db_session: Session
) -> None:
    user = make_user(db_session)
    subscription = make_subscription(
        db_session, user=user, status=SubscriptionStatus.TRIALING.value
    )
    payment = make_payment(
        db_session,
        subscription=subscription,
        payer=user,
        payment_type=PaymentType.SUBSCRIPTION.value,
    )
    db_session.commit()
    activate_or_renew_subscription(db_session, payment)
    db_session.commit()
    token = sign_token(user.id, email=user.email)

    response = client.get(
        f"/api/v1/subscriptions/{subscription.id}/status-history", headers=auth_headers(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert any(entry["to_status"] == "active" for entry in body)
