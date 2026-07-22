"""Reconciliation — see docs/payments.md#10-reconciliation-command. Confirms
payment status directly against a fake "provider API" (never the client),
the fallback path for a lost/delayed webhook."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.enums import BookingStatus
from app.services.payments.base import (
    PaymentProvider,
    ProviderOrder,
    ProviderPaymentStatus,
    ProviderRefund,
    ProviderWebhookEvent,
)
from app.services.payments.service import reconcile_pending_payments
from tests.db.factories import make_artist_profile, make_booking, make_payment, make_user


class _FakeProvider(PaymentProvider):
    """Returns a fixed status per provider_order_id, configured by the test —
    stands in for a real provider's `GET /orders/{id}/payments` call. The
    other methods are never exercised by these tests."""

    def __init__(self, statuses: dict[str, ProviderPaymentStatus]) -> None:
        self._statuses = statuses

    def create_order(
        self, *, amount_minor: int, currency: str, receipt: str, notes: dict[str, str]
    ) -> ProviderOrder:
        raise NotImplementedError

    def verify_webhook_signature(self, *, raw_body: bytes, signature: str) -> bool:
        raise NotImplementedError

    def parse_webhook_event(self, *, raw_body: bytes) -> ProviderWebhookEvent:
        raise NotImplementedError

    def get_order_status(self, *, provider_order_id: str) -> ProviderPaymentStatus:
        return self._statuses[provider_order_id]

    def create_refund(self, *, provider_payment_id: str, amount_minor: int) -> ProviderRefund:
        raise NotImplementedError


def _old_timestamp(minutes: int = 30) -> datetime:
    return datetime.now(UTC) - timedelta(minutes=minutes)


def test_reconcile_settles_a_captured_payment_found_via_the_provider_api(
    db_session: Session,
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
        provider_order_id="order_recon_ok",
        created_at=_old_timestamp(),
    )
    db_session.commit()

    provider = _FakeProvider(
        {
            "order_recon_ok": ProviderPaymentStatus(
                provider_payment_id="pay_recon_ok",
                status="captured",
                amount_minor=50000,
                currency="INR",
                failure_reason=None,
            )
        }
    )

    changed = reconcile_pending_payments(db_session, older_than_minutes=15, provider=provider)

    assert changed == 1
    db_session.refresh(payment)
    assert payment.status == "succeeded"
    assert payment.provider_payment_id == "pay_recon_ok"


def test_reconcile_marks_a_failed_payment_found_via_the_provider_api(db_session: Session) -> None:
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
        provider_order_id="order_recon_fail",
        created_at=_old_timestamp(),
    )
    db_session.commit()

    provider = _FakeProvider(
        {
            "order_recon_fail": ProviderPaymentStatus(
                provider_payment_id="pay_recon_fail",
                status="failed",
                amount_minor=50000,
                currency="INR",
                failure_reason="Card declined.",
            )
        }
    )

    changed = reconcile_pending_payments(db_session, older_than_minutes=15, provider=provider)

    assert changed == 1
    db_session.refresh(payment)
    assert payment.status == "failed"
    assert payment.failure_reason == "Card declined."


def test_reconcile_skips_payments_still_within_the_grace_period(db_session: Session) -> None:
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
        provider_order_id="order_recon_fresh",
        created_at=datetime.now(UTC),
    )
    db_session.commit()

    provider = _FakeProvider(
        {
            "order_recon_fresh": ProviderPaymentStatus(
                provider_payment_id="pay_recon_fresh",
                status="captured",
                amount_minor=50000,
                currency="INR",
                failure_reason=None,
            )
        }
    )

    changed = reconcile_pending_payments(db_session, older_than_minutes=15, provider=provider)

    assert changed == 0
    db_session.refresh(payment)
    assert payment.status == "pending"


def test_reconcile_is_idempotent_when_run_twice(db_session: Session) -> None:
    """A cron-triggered CLI job (app/cli/reconcile_payments.py) can overlap
    or be re-run after a partial failure — re-settling an already-settled
    payment must be a safe no-op, not a duplicate state transition. See
    docs/performance-and-reliability.md#idempotent-tasks."""
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
        provider_order_id="order_recon_idempotent",
        created_at=_old_timestamp(),
    )
    db_session.commit()

    provider = _FakeProvider(
        {
            "order_recon_idempotent": ProviderPaymentStatus(
                provider_payment_id="pay_recon_idempotent",
                status="captured",
                amount_minor=50000,
                currency="INR",
                failure_reason=None,
            )
        }
    )

    first_run = reconcile_pending_payments(db_session, older_than_minutes=15, provider=provider)
    db_session.commit()
    second_run = reconcile_pending_payments(db_session, older_than_minutes=15, provider=provider)

    assert first_run == 1
    # The payment is no longer `pending`, so the second pass's own query
    # (which only selects pending payments) finds nothing left to do.
    assert second_run == 0
    db_session.refresh(payment)
    assert payment.status == "succeeded"
