"""Coupon validation (preview, no redemption) and staff coupon management —
see docs/subscriptions-and-entitlements.md#coupons."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import make_coupon, make_subscription_plan, make_user


def test_validate_a_valid_coupon(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(db_session, target_role="customer", price_amount=200.0)
    coupon = make_coupon(db_session, discount_type="percentage", discount_value=25.0)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/coupons/validate",
        json={"code": coupon.code, "plan_id": str(plan.id)},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["discount_amount"] == 50.0
    assert body["final_amount"] == 150.0


def test_validate_does_not_redeem(client: TestClient, db_session: Session) -> None:
    """Checking a code (e.g. mistyped) must not burn the one-per-user
    redemption — only an actual checkout does."""
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(db_session, target_role="customer", price_amount=200.0)
    coupon = make_coupon(db_session, discount_type="percentage", discount_value=25.0)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    for _ in range(3):
        response = client.post(
            "/api/v1/coupons/validate",
            json={"code": coupon.code, "plan_id": str(plan.id)},
            headers=auth_headers(token),
        )
        assert response.json()["valid"] is True


def test_validate_an_expired_coupon(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(db_session, target_role="customer", price_amount=200.0)
    coupon = make_coupon(
        db_session,
        discount_type="fixed_amount",
        discount_value=10.0,
        valid_from=datetime.now(UTC) - timedelta(days=30),
        valid_until=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/coupons/validate",
        json={"code": coupon.code, "plan_id": str(plan.id)},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_validate_a_coupon_at_its_redemption_cap(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(db_session, target_role="customer", price_amount=200.0)
    coupon = make_coupon(
        db_session,
        discount_type="fixed_amount",
        discount_value=10.0,
        max_redemptions=5,
        redemption_count=5,
    )
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/coupons/validate",
        json={"code": coupon.code, "plan_id": str(plan.id)},
        headers=auth_headers(token),
    )
    assert response.json()["valid"] is False


def test_validate_an_unknown_code(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(db_session, target_role="customer", price_amount=200.0)
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/coupons/validate",
        json={"code": "NOSUCHCODE", "plan_id": str(plan.id)},
        headers=auth_headers(token),
    )
    assert response.json()["valid"] is False


# --- Staff coupon management -----------------------------------------------------


def test_only_staff_can_create_coupons(client: TestClient, db_session: Session) -> None:
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(
        "/api/v1/admin/coupons",
        json={
            "code": "STAFFONLY",
            "discount_type": "percentage",
            "discount_value": 10,
            "valid_from": datetime.now(UTC).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_staff_can_create_and_list_coupons(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    create_response = client.post(
        "/api/v1/admin/coupons",
        json={
            "code": "welcome10",
            "discount_type": "percentage",
            "discount_value": 10,
            "valid_from": datetime.now(UTC).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert create_response.status_code == 201
    assert create_response.json()["code"] == "WELCOME10"  # normalized upper-case

    list_response = client.get("/api/v1/admin/coupons", headers=auth_headers(token))
    assert list_response.status_code == 200
    assert any(c["code"] == "WELCOME10" for c in list_response.json()["items"])


def test_duplicate_coupon_code_is_rejected(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, role="administrator")
    make_coupon(db_session, code="DUPE10")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        "/api/v1/admin/coupons",
        json={
            "code": "DUPE10",
            "discount_type": "percentage",
            "discount_value": 10,
            "valid_from": datetime.now(UTC).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 409
