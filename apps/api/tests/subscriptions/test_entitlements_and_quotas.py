"""Backend-enforced entitlements and usage quotas — see
docs/subscriptions-and-entitlements.md#feature-entitlements-and-usage-
quotas. Every check here goes through the real HTTP route, not the service
function directly, so it also proves the frontend can't be relied on to
hide anything (the explicit "do not rely only on hidden UI" requirement)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.enums import DesignImageStatus
from app.db.models.design import Design, DesignImage
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_artist_profile,
    make_design,
    make_subscription,
    make_subscription_plan,
    make_user,
)


def _make_ready_image(db_session: Session, design: Design) -> DesignImage:
    image = DesignImage(
        design_id=design.id,
        status=DesignImageStatus.READY.value,
        image_url="https://example.test/full.jpg",
        thumbnail_small_url="https://example.test/small.jpg",
        thumbnail_medium_url="https://example.test/medium.jpg",
        is_primary=True,
    )
    db_session.add(image)
    db_session.flush()
    return image


# --- Premium design access ----------------------------------------------------


def test_free_customer_cannot_see_full_images_of_a_premium_design(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile, status="published")
    design.is_premium = True
    db_session.add(design)
    _make_ready_image(db_session, design)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["premium_locked"] is True
    assert body["images"][0]["image_url"] is None
    assert body["images"][0]["thumbnail_small_url"] is not None


def test_premium_customer_can_see_full_images_of_a_premium_design(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile, status="published")
    design.is_premium = True
    db_session.add(design)
    _make_ready_image(db_session, design)
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(
        db_session, target_role="customer", features={"premium_design_access": True}
    )
    make_subscription(db_session, user=customer, plan=plan, status="active")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["premium_locked"] is False
    assert body["images"][0]["image_url"] == "https://example.test/full.jpg"


def test_owner_always_sees_full_images_of_their_own_premium_design(
    client: TestClient, db_session: Session
) -> None:
    owner = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=owner)
    design = make_design(db_session, artist_profile=artist_profile, status="published")
    design.is_premium = True
    db_session.add(design)
    _make_ready_image(db_session, design)
    db_session.commit()
    token = sign_token(owner.id, email=owner.email)

    response = client.get(f"/api/v1/designs/{design.id}", headers=auth_headers(token))
    assert response.json()["premium_locked"] is False


# --- Download limits -----------------------------------------------------------


def test_download_is_blocked_once_the_monthly_quota_is_used_up(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile, status="published")
    _make_ready_image(db_session, design)
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(
        db_session, target_role="customer", features={"download_limit_per_month": 1}
    )
    make_subscription(db_session, user=customer, plan=plan, status="active")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    first = client.post(f"/api/v1/designs/{design.id}/download", headers=auth_headers(token))
    assert first.status_code == 200

    second = client.post(f"/api/v1/designs/{design.id}/download", headers=auth_headers(token))
    assert second.status_code == 403


def test_downloading_a_premium_design_requires_premium_access_even_under_quota(
    client: TestClient, db_session: Session
) -> None:
    artist_profile = make_artist_profile(db_session)
    design = make_design(db_session, artist_profile=artist_profile, status="published")
    design.is_premium = True
    db_session.add(design)
    _make_ready_image(db_session, design)
    customer = make_user(db_session, role="customer")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    response = client.post(f"/api/v1/designs/{design.id}/download", headers=auth_headers(token))
    assert response.status_code == 403


# --- Artist portfolio limits -----------------------------------------------------


def test_publishing_beyond_the_portfolio_limit_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    artist_user = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=artist_user)
    plan = make_subscription_plan(db_session, target_role="artist", features={"portfolio_limit": 1})
    make_subscription(db_session, user=artist_user, plan=plan, status="active")
    first_design = make_design(db_session, artist_profile=artist_profile, status="draft")
    second_design = make_design(db_session, artist_profile=artist_profile, status="draft")
    db_session.commit()
    token = sign_token(artist_user.id, email=artist_user.email)

    first = client.patch(
        f"/api/v1/designs/{first_design.id}",
        json={"status": "published"},
        headers=auth_headers(token),
    )
    assert first.status_code == 200

    second = client.patch(
        f"/api/v1/designs/{second_design.id}",
        json={"status": "published"},
        headers=auth_headers(token),
    )
    assert second.status_code == 403


def test_unlimited_portfolio_plan_has_no_cap(client: TestClient, db_session: Session) -> None:
    artist_user = make_user(db_session, role="artist")
    artist_profile = make_artist_profile(db_session, user=artist_user)
    plan = make_subscription_plan(
        db_session, target_role="artist", features={"portfolio_limit": None}
    )
    make_subscription(db_session, user=artist_user, plan=plan, status="active")
    designs = [
        make_design(db_session, artist_profile=artist_profile, status="draft") for _ in range(3)
    ]
    db_session.commit()
    token = sign_token(artist_user.id, email=artist_user.email)

    for design in designs:
        response = client.patch(
            f"/api/v1/designs/{design.id}",
            json={"status": "published"},
            headers=auth_headers(token),
        )
        assert response.status_code == 200


# --- AI-credit foundation -------------------------------------------------------


def test_ai_generation_is_blocked_once_the_monthly_credit_quota_is_used_up(
    client: TestClient, db_session: Session
) -> None:
    customer = make_user(db_session, role="customer")
    plan = make_subscription_plan(
        db_session, target_role="customer", features={"ai_credits_per_month": 1}
    )
    make_subscription(db_session, user=customer, plan=plan, status="active")
    db_session.commit()
    token = sign_token(customer.id, email=customer.email)

    first = client.post(
        "/api/v1/ai/generations",
        json={"generation_type": "design_discovery", "request_payload": {"query": "bridal"}},
        headers=auth_headers(token),
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/ai/generations",
        json={"generation_type": "design_discovery", "request_payload": {"query": "bridal"}},
        headers=auth_headers(token),
    )
    assert second.status_code == 403
