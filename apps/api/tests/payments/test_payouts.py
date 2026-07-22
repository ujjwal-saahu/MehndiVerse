"""Payout-record foundation — see docs/payments.md#9-payout-record-
foundation."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.payments.service import create_payout_batch
from tests.auth.conftest import auth_headers, sign_token
from tests.db.factories import (
    make_artist_earning,
    make_artist_profile,
    make_payment,
    make_user,
)


def test_create_payout_batch_groups_unpaid_earnings(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    payment_a = make_payment(db_session, status="succeeded")
    payment_b = make_payment(db_session, status="succeeded")
    make_artist_earning(
        db_session,
        payment=payment_a,
        artist_profile=profile,
        gross_amount=50000,
        commission_amount=7500,
        net_amount=42500,
    )
    make_artist_earning(
        db_session,
        payment=payment_b,
        artist_profile=profile,
        gross_amount=20000,
        commission_amount=3000,
        net_amount=17000,
    )
    db_session.commit()

    payout = create_payout_batch(db_session, artist_profile_id=profile.id)
    db_session.commit()

    assert payout is not None
    assert payout.amount == 59500
    assert payout.status == "pending"


def test_create_payout_batch_is_none_when_nothing_to_pay_out(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()

    payout = create_payout_batch(db_session, artist_profile_id=profile.id)

    assert payout is None


def test_earnings_already_paid_out_are_excluded_from_a_new_batch(db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    payment = make_payment(db_session, status="succeeded")
    make_artist_earning(
        db_session,
        payment=payment,
        artist_profile=profile,
        gross_amount=50000,
        commission_amount=7500,
        net_amount=42500,
    )
    db_session.commit()

    first = create_payout_batch(db_session, artist_profile_id=profile.id)
    db_session.commit()
    assert first is not None

    second = create_payout_batch(db_session, artist_profile_id=profile.id)
    assert second is None


def test_non_staff_cannot_create_a_payout_batch(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    db_session.commit()
    token = sign_token(profile.user_id, email="artist@example.com")

    response = client.post(
        f"/api/v1/admin/payments/artists/{profile.id}/payouts", headers=auth_headers(token)
    )
    assert response.status_code == 403


def test_staff_can_create_a_payout_batch(client: TestClient, db_session: Session) -> None:
    profile = make_artist_profile(db_session)
    payment = make_payment(db_session, status="succeeded")
    make_artist_earning(
        db_session,
        payment=payment,
        artist_profile=profile,
        gross_amount=50000,
        commission_amount=7500,
        net_amount=42500,
    )
    admin = make_user(db_session, role="administrator")
    db_session.commit()
    token = sign_token(admin.id, email=admin.email)

    response = client.post(
        f"/api/v1/admin/payments/artists/{profile.id}/payouts", headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["amount"] == 42500
