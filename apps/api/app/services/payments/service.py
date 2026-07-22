"""Booking payment orchestration — see docs/payments.md.

`create_payment_order()`, the webhook dispatcher, and `reconcile_pending_
payments()` are the three ways a payment's status can ever change — no
route handler assigns `Payment.status` directly. Success is only ever
applied via `_settle_payment()`, called either from a verified webhook or
from reconciliation's direct provider-API poll — **never** from a client
simply reporting "payment succeeded" (see
docs/payments.md#4-never-trust-client-reported-success).
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.alerts import send_alert
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.metrics import observe_payment_webhook
from app.db.enums import (
    AnalyticsEventType,
    BookingStatus,
    NotificationType,
    PaymentStatus,
    PaymentType,
    PayoutStatus,
    RefundStatus,
)
from app.db.models.artist import ArtistProfile
from app.db.models.booking import Booking
from app.db.models.payment import ArtistEarning, Payment, PaymentWebhookEvent, Payout, Refund
from app.db.models.system import AuditLog
from app.services.analytics.events import record_event
from app.services.booking import transition_booking
from app.services.notifications import notify_user
from app.services.payments.base import PaymentProvider
from app.services.payments.commission import calculate_commission
from app.services.payments.factory import get_payment_provider
from app.services.subscriptions import (
    activate_or_renew_subscription,
    handle_failed_subscription_payment,
)

_SUCCESS_STATUSES = frozenset({"captured", "authorized"})
_FAILURE_STATUSES = frozenset({"failed"})


def _record_audit(
    db: Session,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    after_state: dict[str, Any] | None = None,
) -> None:
    """Financial audit trail — see docs/payments.md#11-financial-audit-
    events. Reuses the generic `audit_logs` table (Phase 10) rather than a
    payments-specific table; `ip_address`/`user_agent` are left null since
    most callers here are webhook/system-triggered, not a live HTTP request
    with a client the way app/services/audit.py::record_audit_log assumes."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            after_state=after_state,
        )
    )


def to_minor_units(major_amount: float) -> int:
    return int(round(major_amount * 100))


# --- Order creation / server-side amount determination -----------------------


def _sum_succeeded_payments_minor(db: Session, booking_id: uuid.UUID) -> int:
    payments = (
        db.execute(
            select(Payment).where(
                Payment.booking_id == booking_id, Payment.status == PaymentStatus.SUCCEEDED.value
            )
        )
        .scalars()
        .all()
    )
    return sum(p.amount for p in payments)


def determine_payment_amount_minor(db: Session, booking: Booking, payment_type: str) -> int:
    """Server-side amount validation starts here: the amount is *always*
    derived from the booking's own stored quote/total, never accepted from
    the client — see docs/payments.md#4."""
    if payment_type == PaymentType.DEPOSIT.value:
        if booking.status != BookingStatus.DEPOSIT_PENDING.value:
            raise AppError(
                "A deposit can only be paid while the booking is awaiting one.", status_code=422
            )
        if booking.deposit_amount is None:
            raise AppError("This booking has no deposit amount set.", status_code=422)
        return to_minor_units(booking.deposit_amount)

    if payment_type == PaymentType.FULL.value:
        if booking.status != BookingStatus.CONFIRMED.value:
            raise AppError(
                "Full payment is only available for a confirmed booking with no deposit due.",
                status_code=422,
            )
        if booking.total_amount is None:
            raise AppError("This booking has no total amount set.", status_code=422)
        return to_minor_units(booking.total_amount)

    if payment_type == PaymentType.BALANCE.value:
        if booking.status != BookingStatus.DEPOSIT_PAID.value:
            raise AppError(
                "The remaining balance can only be paid after the deposit.", status_code=422
            )
        if booking.total_amount is None:
            raise AppError("This booking has no total amount set.", status_code=422)
        remaining = to_minor_units(booking.total_amount) - _sum_succeeded_payments_minor(
            db, booking.id
        )
        if remaining <= 0:
            raise AppError("There is nothing left to pay on this booking.", status_code=422)
        return remaining

    raise AppError(f"Unknown payment_type: {payment_type!r}", status_code=422)


def create_payment_order(
    db: Session,
    booking: Booking,
    *,
    payment_type: str,
    payer_id: uuid.UUID,
    idempotency_key: str | None,
    provider: PaymentProvider | None = None,
) -> tuple[Payment, str]:
    """Returns (payment, provider_key_id) — the key id is safe to hand to a
    client (it's publishable, not a secret) so it can launch the provider's
    checkout against `payment.provider_order_id`."""
    if idempotency_key:
        existing = db.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing is not None:
            return existing, get_settings().razorpay_key_id

    existing_active = (
        db.execute(
            select(Payment).where(
                Payment.booking_id == booking.id,
                Payment.payment_type == payment_type,
                Payment.status.in_([PaymentStatus.PENDING.value, PaymentStatus.SUCCEEDED.value]),
            )
        )
        .scalars()
        .all()
    )
    for candidate in existing_active:
        if candidate.status == PaymentStatus.SUCCEEDED.value:
            raise AppError(f"This booking's {payment_type} has already been paid.", status_code=409)
        # A PENDING order for the same purpose already exists — hand back
        # the same order rather than creating a second one the provider
        # would happily accept (a customer double-tapping "Pay" shouldn't
        # ever produce two live orders for the same charge).
        return candidate, get_settings().razorpay_key_id

    amount_minor = determine_payment_amount_minor(db, booking, payment_type)
    provider = provider or get_payment_provider()
    order = provider.create_order(
        amount_minor=amount_minor,
        currency=booking.currency,
        receipt=f"booking:{booking.id}:{payment_type}",
        notes={"booking_id": str(booking.id), "payment_type": payment_type},
    )

    payment = Payment(
        booking_id=booking.id,
        payer_id=payer_id,
        amount=amount_minor,
        currency=booking.currency,
        provider="razorpay",
        provider_order_id=order.provider_order_id,
        payment_type=payment_type,
        idempotency_key=idempotency_key,
    )
    db.add(payment)
    db.flush()
    _record_audit(
        db,
        actor_id=payer_id,
        action="payment.order_created",
        entity_type="payments",
        entity_id=payment.id,
        after_state={"amount": amount_minor, "currency": booking.currency, "type": payment_type},
    )
    return payment, order.provider_key_id


# --- Webhook handling ----------------------------------------------------------


def handle_webhook(db: Session, *, raw_body: bytes, signature: str | None) -> None:
    provider = get_payment_provider()
    if not signature or not provider.verify_webhook_signature(
        raw_body=raw_body, signature=signature
    ):
        # Payment-webhook monitoring — see docs/observability.md#payment-
        # failures. A spike here is either a misconfigured webhook secret
        # or a spoofing attempt (see docs/incident-response.md#payment-
        # webhook-anomaly-signature-failures-unexpected-event-volume) —
        # not, by itself, evidence of a breach.
        observe_payment_webhook("signature_invalid")
        raise AppError("Invalid webhook signature.", status_code=400)

    event = provider.parse_webhook_event(raw_body=raw_body)
    reference = event.provider_payment_id or event.provider_refund_id or event.provider_order_id
    if reference is None:
        observe_payment_webhook("error")
        send_alert("payment_webhook_unreferenced_event", event_type=event.event_type)
        raise AppError("Webhook event has no identifiable reference.", status_code=400)

    try:
        with db.begin_nested():
            db.add(
                PaymentWebhookEvent(
                    provider="razorpay",
                    event_type=event.event_type,
                    provider_reference=reference,
                    payload=event.raw,
                )
            )
            db.flush()
    except IntegrityError:
        # Already processed this exact event — a SAVEPOINT (`begin_nested`)
        # means only this insert unwinds, not the whole request's
        # transaction — see
        # docs/payments.md#5-signed-webhook-handling-and-duplicate-protection.
        observe_payment_webhook("duplicate")
        return

    if event.event_type in ("payment.captured", "payment.authorized"):
        observe_payment_webhook("settled")
        _settle_payment(
            db,
            provider_order_id=event.provider_order_id,
            provider_payment_id=event.provider_payment_id,
            amount_minor=event.amount_minor,
            provider_status=event.status,
            failure_reason=None,
        )
    elif event.event_type == "payment.failed":
        # Payment failure — see docs/observability.md#payment-failures.
        observe_payment_webhook("payment_failed")
        _settle_payment(
            db,
            provider_order_id=event.provider_order_id,
            provider_payment_id=event.provider_payment_id,
            amount_minor=event.amount_minor,
            provider_status=event.status,
            failure_reason=event.failure_reason,
        )
    elif event.event_type in ("refund.processed", "refund.created"):
        observe_payment_webhook("refund")
        _apply_refund_update(db, provider_refund_id=event.provider_refund_id, status=event.status)
    else:
        # Any other event type is intentionally ignored — not every Razorpay
        # webhook event concerns a booking payment this app tracks.
        observe_payment_webhook("ignored")


# --- Settling a payment (webhook OR reconciliation) ---------------------------


def _settle_payment(
    db: Session,
    *,
    provider_order_id: str | None,
    provider_payment_id: str | None,
    amount_minor: int | None,
    provider_status: str,
    failure_reason: str | None,
) -> None:
    if provider_order_id is None:
        return
    payment = db.execute(
        select(Payment).where(Payment.provider_order_id == provider_order_id)
    ).scalar_one_or_none()
    if payment is None:
        _record_audit(
            db,
            actor_id=None,
            action="payment.unknown_order_referenced",
            entity_type="payments",
            entity_id=None,
            after_state={"provider_order_id": provider_order_id},
        )
        return
    if payment.status in (PaymentStatus.SUCCEEDED.value, PaymentStatus.FAILED.value):
        return  # already settled — idempotent no-op.

    if payment.subscription_id is not None:
        _settle_subscription_payment(
            db,
            payment=payment,
            provider_payment_id=provider_payment_id,
            amount_minor=amount_minor,
            provider_status=provider_status,
            failure_reason=failure_reason,
        )
        return

    if provider_status in _SUCCESS_STATUSES:
        # Server-side amount validation — see docs/payments.md#4. Never
        # credit a payment for more (or less) than the order was created
        # for, no matter what the provider claims occurred.
        if amount_minor is not None and amount_minor != payment.amount:
            payment.status = PaymentStatus.FAILED.value
            payment.failure_reason = (
                f"Amount mismatch: expected {payment.amount}, provider reported {amount_minor}."
            )
            db.add(payment)
            _record_audit(
                db,
                actor_id=None,
                action="payment.amount_mismatch",
                entity_type="payments",
                entity_id=payment.id,
                after_state={"expected": payment.amount, "reported": amount_minor},
            )
            return

        payment.status = PaymentStatus.SUCCEEDED.value
        payment.provider_payment_id = provider_payment_id
        payment.paid_at = datetime.now(UTC)

        split = calculate_commission(payment.amount, get_settings().platform_commission_percent)
        payment.commission_amount = split.commission_amount
        payment.net_amount = split.net_amount
        db.add(payment)

        booking = db.get(Booking, payment.booking_id)
        assert booking is not None
        artist_profile = db.get(ArtistProfile, booking.artist_profile_id)
        assert artist_profile is not None

        db.add(
            ArtistEarning(
                artist_profile_id=artist_profile.id,
                booking_id=booking.id,
                payment_id=payment.id,
                gross_amount=split.gross_amount,
                commission_amount=split.commission_amount,
                net_amount=split.net_amount,
                currency=payment.currency,
            )
        )

        if (
            payment.payment_type == PaymentType.DEPOSIT.value
            and booking.status == BookingStatus.DEPOSIT_PENDING.value
        ):
            transition_booking(
                db,
                booking,
                to_status=BookingStatus.DEPOSIT_PAID.value,
                changed_by=None,
                reason="Deposit paid.",
            )

        _record_audit(
            db,
            actor_id=None,
            action="payment.succeeded",
            entity_type="payments",
            entity_id=payment.id,
            after_state={
                "amount": payment.amount,
                "commission_amount": split.commission_amount,
                "net_amount": split.net_amount,
            },
        )

        for user_id in {booking.customer_id, artist_profile.user_id}:
            notify_user(
                db,
                user_id=user_id,
                notification_type=NotificationType.PAYMENT.value,
                title="Payment received",
                body=f"A {payment.payment_type} payment of {payment.currency} "
                f"{payment.amount / 100:.2f} was received.",
                data={"booking_id": str(booking.id), "payment_id": str(payment.id)},
            )

        record_event(
            db,
            event_type=AnalyticsEventType.PAYMENT_COMPLETED.value,
            user_id=payment.payer_id,
            entity_type="payment",
            entity_id=payment.id,
            properties={"payment_type": payment.payment_type, "currency": payment.currency},
        )

    elif provider_status in _FAILURE_STATUSES:
        payment.status = PaymentStatus.FAILED.value
        payment.failure_reason = failure_reason or "Payment failed."
        payment.provider_payment_id = provider_payment_id
        db.add(payment)
        _record_audit(
            db,
            actor_id=None,
            action="payment.failed",
            entity_type="payments",
            entity_id=payment.id,
            after_state={"failure_reason": payment.failure_reason},
        )
        notify_user(
            db,
            user_id=payment.payer_id,
            notification_type=NotificationType.PAYMENT.value,
            title="Payment failed",
            body=payment.failure_reason,
            data={"booking_id": str(payment.booking_id), "payment_id": str(payment.id)},
        )
    # Any other provider status (e.g. still "created") is not yet a
    # terminal outcome — nothing to settle.


def _settle_subscription_payment(
    db: Session,
    *,
    payment: Payment,
    provider_payment_id: str | None,
    amount_minor: int | None,
    provider_status: str,
    failure_reason: str | None,
) -> None:
    """A subscription checkout's payment settles through this same webhook/
    reconciliation path — see docs/subscriptions-and-entitlements.md
    #subscription-checkout-reuses-payments. No commission split or
    `ArtistEarning` here: subscription revenue isn't attributed to any one
    artist the way a booking payment is."""
    if provider_status in _SUCCESS_STATUSES:
        if amount_minor is not None and amount_minor != payment.amount:
            payment.status = PaymentStatus.FAILED.value
            payment.failure_reason = (
                f"Amount mismatch: expected {payment.amount}, provider reported {amount_minor}."
            )
            db.add(payment)
            _record_audit(
                db,
                actor_id=None,
                action="payment.amount_mismatch",
                entity_type="payments",
                entity_id=payment.id,
                after_state={"expected": payment.amount, "reported": amount_minor},
            )
            return

        payment.status = PaymentStatus.SUCCEEDED.value
        payment.provider_payment_id = provider_payment_id
        payment.paid_at = datetime.now(UTC)
        db.add(payment)

        activate_or_renew_subscription(db, payment)

        _record_audit(
            db,
            actor_id=None,
            action="payment.succeeded",
            entity_type="payments",
            entity_id=payment.id,
            after_state={"amount": payment.amount, "subscription_id": str(payment.subscription_id)},
        )
        record_event(
            db,
            event_type=AnalyticsEventType.PAYMENT_COMPLETED.value,
            user_id=payment.payer_id,
            entity_type="payment",
            entity_id=payment.id,
            properties={"payment_type": payment.payment_type, "currency": payment.currency},
        )

    elif provider_status in _FAILURE_STATUSES:
        payment.status = PaymentStatus.FAILED.value
        payment.failure_reason = failure_reason or "Payment failed."
        payment.provider_payment_id = provider_payment_id
        db.add(payment)

        handle_failed_subscription_payment(db, payment)

        _record_audit(
            db,
            actor_id=None,
            action="payment.failed",
            entity_type="payments",
            entity_id=payment.id,
            after_state={"failure_reason": payment.failure_reason},
        )
    # Any other provider status is not yet a terminal outcome.


def _apply_refund_update(db: Session, *, provider_refund_id: str | None, status: str) -> None:
    if provider_refund_id is None:
        return
    refund = db.execute(
        select(Refund).where(Refund.provider_refund_id == provider_refund_id)
    ).scalar_one_or_none()
    if refund is None:
        _record_audit(
            db,
            actor_id=None,
            action="refund.unknown_reference",
            entity_type="refunds",
            entity_id=None,
            after_state={"provider_refund_id": provider_refund_id},
        )
        return
    if refund.status == RefundStatus.PROCESSED.value:
        return

    if status == "processed":
        refund.status = RefundStatus.PROCESSED.value
        refund.processed_at = datetime.now(UTC)
        db.add(refund)

        payment = db.get(Payment, refund.payment_id)
        assert payment is not None
        total_refunded = (
            db.execute(
                select(Refund).where(
                    Refund.payment_id == payment.id, Refund.status == RefundStatus.PROCESSED.value
                )
            )
            .scalars()
            .all()
        )
        refunded_amount = sum(r.amount for r in total_refunded)
        payment.status = (
            PaymentStatus.REFUNDED.value
            if refunded_amount >= payment.amount
            else PaymentStatus.PARTIALLY_REFUNDED.value
        )
        db.add(payment)

        _record_audit(
            db,
            actor_id=None,
            action="refund.processed",
            entity_type="refunds",
            entity_id=refund.id,
            after_state={"amount": refund.amount},
        )
        notify_user(
            db,
            user_id=payment.payer_id,
            notification_type=NotificationType.PAYMENT.value,
            title="Refund processed",
            body=f"Your refund of {refund.currency} {refund.amount / 100:.2f} was processed.",
            data={"payment_id": str(payment.id), "refund_id": str(refund.id)},
        )


# --- Refund request / approval --------------------------------------------------


def request_refund(
    db: Session, payment: Payment, *, requested_by: uuid.UUID, reason: str | None
) -> Refund:
    if payment.status not in (
        PaymentStatus.SUCCEEDED.value,
        PaymentStatus.PARTIALLY_REFUNDED.value,
    ):
        raise AppError("Only a successful payment can be refunded.", status_code=422)

    existing_open = db.execute(
        select(Refund).where(
            Refund.payment_id == payment.id,
            Refund.status.in_([RefundStatus.PENDING.value, RefundStatus.APPROVED.value]),
        )
    ).first()
    if existing_open is not None:
        raise AppError("A refund is already in progress for this payment.", status_code=409)

    processed = (
        db.execute(
            select(Refund).where(
                Refund.payment_id == payment.id, Refund.status == RefundStatus.PROCESSED.value
            )
        )
        .scalars()
        .all()
    )
    already_refunded = sum(r.amount for r in processed)
    refundable = payment.amount - already_refunded
    if refundable <= 0:
        raise AppError("This payment has already been fully refunded.", status_code=422)

    refund = Refund(
        payment_id=payment.id,
        amount=refundable,
        currency=payment.currency,
        reason=reason,
        status=RefundStatus.PENDING.value,
        requested_at=datetime.now(UTC),
    )
    db.add(refund)
    db.flush()
    _record_audit(
        db,
        actor_id=requested_by,
        action="refund.requested",
        entity_type="refunds",
        entity_id=refund.id,
        after_state={"amount": refundable, "reason": reason},
    )
    return refund


def approve_refund(
    db: Session, refund: Refund, *, approved_by: uuid.UUID, provider: PaymentProvider | None = None
) -> None:
    if refund.status != RefundStatus.PENDING.value:
        raise AppError("Only a pending refund can be approved.", status_code=422)
    payment = db.get(Payment, refund.payment_id)
    assert payment is not None
    if payment.provider_payment_id is None:
        raise AppError(
            "This payment has no confirmed provider payment id to refund yet.", status_code=422
        )

    provider = provider or get_payment_provider()
    result = provider.create_refund(
        provider_payment_id=payment.provider_payment_id, amount_minor=refund.amount
    )
    refund.status = RefundStatus.APPROVED.value
    refund.provider_refund_id = result.provider_refund_id
    refund.processed_by = approved_by
    db.add(refund)
    _record_audit(
        db,
        actor_id=approved_by,
        action="refund.approved",
        entity_type="refunds",
        entity_id=refund.id,
        after_state={"provider_refund_id": result.provider_refund_id},
    )


def reject_refund(
    db: Session, refund: Refund, *, rejected_by: uuid.UUID, reason: str | None
) -> None:
    if refund.status != RefundStatus.PENDING.value:
        raise AppError("Only a pending refund can be rejected.", status_code=422)
    refund.status = RefundStatus.REJECTED.value
    refund.processed_by = rejected_by
    refund.processed_at = datetime.now(UTC)
    db.add(refund)
    _record_audit(
        db,
        actor_id=rejected_by,
        action="refund.rejected",
        entity_type="refunds",
        entity_id=refund.id,
        after_state={"reason": reason},
    )


# --- Payout-record foundation ---------------------------------------------------


def create_payout_batch(db: Session, *, artist_profile_id: uuid.UUID) -> Payout | None:
    """See docs/payments.md#9-payout-record-foundation. Does not execute an
    actual bank transfer — only groups unpaid earnings into a `Payout`
    record for a future payouts phase to action."""
    earnings = (
        db.execute(
            select(ArtistEarning).where(
                ArtistEarning.artist_profile_id == artist_profile_id,
                ArtistEarning.payout_id.is_(None),
            )
        )
        .scalars()
        .all()
    )
    if not earnings:
        return None

    total = sum(e.net_amount for e in earnings)
    currency = earnings[0].currency
    payout = Payout(
        artist_profile_id=artist_profile_id,
        amount=total,
        currency=currency,
        status=PayoutStatus.PENDING.value,
        requested_at=datetime.now(UTC),
    )
    db.add(payout)
    db.flush()
    for earning in earnings:
        earning.payout_id = payout.id
        db.add(earning)
    _record_audit(
        db,
        actor_id=None,
        action="payout.created",
        entity_type="payouts",
        entity_id=payout.id,
        after_state={"amount": total, "earning_count": len(earnings)},
    )
    return payout


# --- Reconciliation --------------------------------------------------------------


def reconcile_pending_payments(
    db: Session, *, older_than_minutes: int = 15, provider: PaymentProvider | None = None
) -> int:
    """Confirms payment status directly against the provider API for any
    order that's been sitting PENDING too long — the "or provider API" half
    of "confirm payment through a verified webhook or provider API." See
    docs/payments.md#10-reconciliation-command. Returns the number of
    payments whose status changed."""
    provider = provider or get_payment_provider()
    cutoff = datetime.now(UTC) - timedelta(minutes=older_than_minutes)
    pending = (
        db.execute(
            select(Payment).where(
                Payment.status == PaymentStatus.PENDING.value, Payment.created_at < cutoff
            )
        )
        .scalars()
        .all()
    )

    changed = 0
    for payment in pending:
        result = provider.get_order_status(provider_order_id=payment.provider_order_id)
        if result.status in _SUCCESS_STATUSES or result.status in _FAILURE_STATUSES:
            _settle_payment(
                db,
                provider_order_id=payment.provider_order_id,
                provider_payment_id=result.provider_payment_id,
                amount_minor=result.amount_minor,
                provider_status=result.status,
                failure_reason=result.failure_reason,
            )
            changed += 1
    return changed
