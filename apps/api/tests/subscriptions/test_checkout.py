"""Subscription checkout — mirrors tests/payments/test_order_creation.py's
structure for the booking-payment equivalent. See
docs/subscriptions-and-entitlements.md#subscription-checkout."""

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.marketing import CouponRedemption
from app.db.models.payment import Payment
from app.db.models.subscription import Subscription
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_coupon, make_subscription_plan, make_user

_ORDER_RESPONSE = {
    "id": "order_sub123",
    "entity": "order",
    "amount": 19900,
    "amount_paid": 0,
    "amount_due": 19900,
    "currency": "INR",
    "status": "created",
}


def _mock_order_creation(razorpay_mock, response: dict | None = None):  # type: ignore[no-untyped-def]
    return razorpay_mock.post("/orders").mock(
        return_value=httpx.Response(200, json=response or _ORDER_RESPONSE)
    )


def test_list_plans_is_public(client: TestClient, db_session: Session) -> None:
    make_subscription_plan(db_session, name="Test Custom Plan", price_amount=199.0)
    db_session.commit()

    response = client.get("/api/v1/subscriptions/plans")
    assert response.status_code == 200
    assert any(p["name"] == "Test Custom Plan" for p in response.json())


def test_checkout_requires_authentication(client: TestClient, db_session: Session) -> None:
    plan = make_subscription_plan(db_session, price_amount=199.0)
    db_session.commit()

    response = client.post("/api/v1/subscriptions/checkout", json={"plan_id": str(plan.id)})
    assert response.status_code == 401


def test_free_plan_cannot_be_checked_out(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(db_session, target_role="customer", price_amount=0.0)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_id": str(plan.id)},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_artist_cannot_check_out_a_customer_plan(client: TestClient, db_session: Session) -> None:
    artist = make_user(db_session, role="artist")
    plan = make_subscription_plan(db_session, target_role="customer", price_amount=199.0)
    db_session.commit()
    token = sign_token(artist.id, email=artist.email)

    response = client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_id": str(plan.id)},
        headers=auth_headers(token),
    )
    assert response.status_code == 422


def test_checkout_creates_a_pending_subscription_and_order(
    client: TestClient, db_session: Session, razorpay_mock
) -> None:
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(db_session, target_role="customer", price_amount=199.0)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    route = _mock_order_creation(razorpay_mock)

    response = client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_id": str(plan.id)},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == 19900
    assert body["status"] == "pending"
    assert route.call_count == 1

    subscription = db_session.execute(
        select(Subscription).where(Subscription.user_id == customer.id)
    ).scalar_one()
    assert subscription.status == "trialing"
    assert subscription.plan_id == plan.id


def test_checkout_idempotency_key_reuses_the_same_order(
    client: TestClient, db_session: Session, razorpay_mock
) -> None:
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(db_session, target_role="customer", price_amount=199.0)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    route = _mock_order_creation(razorpay_mock)

    first = client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_id": str(plan.id), "idempotency_key": "sub-key-1"},
        headers=auth_headers(token),
    ).json()
    second = client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_id": str(plan.id), "idempotency_key": "sub-key-1"},
        headers=auth_headers(token),
    ).json()

    assert first["payment_id"] == second["payment_id"]
    assert route.call_count == 1


def test_checkout_applies_a_valid_coupon_and_redeems_it(
    client: TestClient, db_session: Session, razorpay_mock
) -> None:
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(db_session, target_role="customer", price_amount=200.0)
    coupon = make_coupon(db_session, discount_type="percentage", discount_value=50.0)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    route = _mock_order_creation(razorpay_mock, {**_ORDER_RESPONSE, "amount": 10000})

    response = client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_id": str(plan.id), "coupon_code": coupon.code},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    assert response.json()["amount"] == 10000
    call_body = route.calls.last.request.content
    assert b'"amount":10000' in call_body

    redemption = db_session.execute(
        select(CouponRedemption).where(
            CouponRedemption.coupon_id == coupon.id, CouponRedemption.user_id == customer.id
        )
    ).scalar_one()
    assert float(redemption.discount_applied) == 100.0
    db_session.refresh(coupon)
    assert coupon.redemption_count == 1


def test_checkout_rejects_an_already_redeemed_coupon(
    client: TestClient, db_session: Session, razorpay_mock
) -> None:
    """Prevent repeated coupon abuse — the same user cannot benefit from the
    same coupon twice, enforced by `uq_coupon_redemptions_coupon_user`."""
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(db_session, target_role="customer", price_amount=200.0)
    coupon = make_coupon(db_session, discount_type="fixed_amount", discount_value=20.0)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)
    _mock_order_creation(razorpay_mock)

    first = client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_id": str(plan.id), "coupon_code": coupon.code},
        headers=auth_headers(token),
    )
    assert first.status_code == 201

    # Force the first order out of `pending` so the second checkout attempt
    # actually re-prices a fresh order (and re-hits coupon validation)
    # instead of just handing back the same still-open order.
    payment = db_session.get(Payment, first.json()["payment_id"])
    assert payment is not None
    payment.status = "succeeded"
    db_session.add(payment)
    db_session.commit()

    second = client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_id": str(plan.id), "coupon_code": coupon.code},
        headers=auth_headers(token),
    )
    assert second.status_code == 409
