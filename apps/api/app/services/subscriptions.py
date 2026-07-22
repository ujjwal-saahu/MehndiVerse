"""Subscription lifecycle: checkout, renewal, cancellation, expiration, and
grace period — see docs/subscriptions-and-entitlements.md.

Subscription checkout reuses the exact same `Payment`/webhook/reconciliation
machinery a booking payment does (`payments.subscription_id` instead of
`payments.booking_id` — see the Phase 18 migration) rather than a parallel
recurring-billing integration; `payments/service.py::_settle_payment()`
branches on which one is set and calls `activate_or_renew_subscription()`/
`handle_failed_subscription_payment()` here instead of the booking-earning
path. No task-queue/scheduler infrastructure exists in this environment (see
docs/payments.md#10-reconciliation-command for the same constraint on
payment reconciliation) — `process_due_subscriptions()` is a standalone,
manually (or externally cron-)triggered function via
`app/cli/process_subscriptions.py`, exactly mirroring
`reconcile_pending_payments()`.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.enums import (
    AnalyticsEventType,
    BillingInterval,
    NotificationType,
    PaymentStatus,
    PaymentType,
    SubscriptionStatus,
    UserRole,
)
from app.db.models.payment import Payment
from app.db.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatusHistory
from app.db.models.system import AuditLog
from app.db.models.user import User
from app.services.analytics.events import record_event
from app.services.coupons import price_coupon, redeem_coupon
from app.services.notifications import notify_user
from app.services.payments.base import PaymentProvider
from app.services.payments.factory import get_payment_provider


def _record_audit(
    db: Session,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    after_state: dict[str, Any] | None = None,
) -> None:
    """Local audit-write helper, matching
    app/services/payments/service.py::_record_audit exactly — most callers
    here are webhook/system-triggered, not a live HTTP request with a
    client, so app/services/audit.py's Request-based helper doesn't fit."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            after_state=after_state,
        )
    )


def _role_for_user(user: User) -> str:
    return "artist" if user.role == UserRole.ARTIST.value else "customer"


def _interval_delta(billing_interval: str) -> timedelta:
    if billing_interval == BillingInterval.YEARLY.value:
        return timedelta(days=365)
    return timedelta(days=30)


def to_minor_units(major_amount: float) -> int:
    return int(round(major_amount * 100))


def _record_status_change(
    db: Session,
    subscription: Subscription,
    *,
    to_status: str,
    reason: str | None,
    changed_by: uuid.UUID | None,
) -> None:
    from_status = subscription.status
    subscription.status = to_status
    db.add(subscription)
    db.add(
        SubscriptionStatusHistory(
            subscription_id=subscription.id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            changed_by=changed_by,
        )
    )


# --- Checkout ----------------------------------------------------------------


def _get_or_create_pending_subscription(
    db: Session, *, user: User, plan: SubscriptionPlan
) -> Subscription:
    """Reuses the user's existing subscription row (of any active-ish
    status) if one exists — a second checkout for the same membership is a
    renewal or plan change, not a second membership. Otherwise creates a new
    row in `trialing`, the model's own default status, with a *placeholder*
    period that only becomes real entitlements once a payment actually
    succeeds (see docs/subscriptions-and-entitlements.md#subscription-
    checkout-reuses-payments — `trialing` never satisfies
    app/core/authz.py::get_effective_role's `status == active` check)."""
    existing = (
        db.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status.in_(
                    [
                        SubscriptionStatus.TRIALING.value,
                        SubscriptionStatus.ACTIVE.value,
                        SubscriptionStatus.PAST_DUE.value,
                    ]
                ),
            )
        )
        .scalars()
        .first()
    )
    if existing is not None:
        if existing.plan_id != plan.id:
            existing.plan_id = plan.id
            db.add(existing)
        return existing

    now = datetime.now(UTC)
    subscription = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status=SubscriptionStatus.TRIALING.value,
        current_period_start=now,
        current_period_end=now + _interval_delta(plan.billing_interval),
        started_at=now,
    )
    db.add(subscription)
    db.flush()
    db.add(
        SubscriptionStatusHistory(
            subscription_id=subscription.id,
            from_status=None,
            to_status=SubscriptionStatus.TRIALING.value,
            reason="Checkout started.",
            changed_by=user.id,
        )
    )
    return subscription


def create_subscription_checkout(
    db: Session,
    *,
    user: User,
    plan: SubscriptionPlan,
    coupon_code: str | None,
    idempotency_key: str | None,
    provider: PaymentProvider | None = None,
) -> tuple[Payment, str]:
    """Returns (payment, provider_key_id) — same contract as
    app/services/payments/service.py::create_payment_order."""
    if not plan.is_active:
        raise AppError("This plan is not currently available.", status_code=422)
    if plan.target_role != _role_for_user(user):
        raise AppError("This plan is not available for your account type.", status_code=422)
    if float(plan.price_amount) <= 0:
        raise AppError("This plan does not require checkout.", status_code=422)

    if idempotency_key:
        existing = db.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing is not None:
            return existing, get_settings().razorpay_key_id

    subscription = _get_or_create_pending_subscription(db, user=user, plan=plan)

    existing_pending = (
        db.execute(
            select(Payment).where(
                Payment.subscription_id == subscription.id,
                Payment.status == PaymentStatus.PENDING.value,
            )
        )
        .scalars()
        .first()
    )
    if existing_pending is not None:
        return existing_pending, get_settings().razorpay_key_id

    amount_major = float(plan.price_amount)
    coupon = None
    discount_amount = 0.0
    if coupon_code:
        coupon, discount_amount = price_coupon(
            db, code=coupon_code, user_id=user.id, amount=amount_major
        )
        amount_major = max(amount_major - discount_amount, 0.0)
    # A 100%-off coupon still produces a >0 order — real money movement (even
    # a token amount) is what confirms the customer's payment method through
    # the provider; see docs/subscriptions-and-entitlements.md#coupons.
    amount_minor = max(to_minor_units(amount_major), 1)

    provider = provider or get_payment_provider()
    order = provider.create_order(
        amount_minor=amount_minor,
        currency=plan.currency,
        receipt=f"subscription:{subscription.id}:{plan.id}",
        notes={"subscription_id": str(subscription.id), "plan_id": str(plan.id)},
    )

    payment = Payment(
        subscription_id=subscription.id,
        payer_id=user.id,
        amount=amount_minor,
        currency=plan.currency,
        provider="razorpay",
        provider_order_id=order.provider_order_id,
        payment_type=PaymentType.SUBSCRIPTION.value,
        idempotency_key=idempotency_key,
    )
    db.add(payment)
    db.flush()

    if coupon is not None:
        redeem_coupon(
            db,
            coupon,
            user_id=user.id,
            subscription_id=subscription.id,
            discount_applied=discount_amount,
        )

    _record_audit(
        db,
        actor_id=user.id,
        action="subscription.checkout_started",
        entity_type="payments",
        entity_id=payment.id,
        after_state={"plan_id": str(plan.id), "amount": amount_minor},
    )
    return payment, order.provider_key_id


# --- Settlement (called from the payment webhook / reconciliation) -----------


def activate_or_renew_subscription(db: Session, payment: Payment) -> None:
    assert payment.subscription_id is not None
    subscription = db.get(Subscription, payment.subscription_id)
    assert subscription is not None
    plan = db.get(SubscriptionPlan, subscription.plan_id)
    assert plan is not None

    now = datetime.now(UTC)
    # First activation starts from now; a renewal chains from wherever the
    # last period ended so paying a few days early/late never shifts the
    # customer's billing anchor date.
    is_first_activation = subscription.status == SubscriptionStatus.TRIALING.value
    period_start = now if is_first_activation else subscription.current_period_end
    period_end = period_start + _interval_delta(plan.billing_interval)

    subscription.current_period_start = period_start
    subscription.current_period_end = period_end
    subscription.grace_period_ends_at = None
    subscription.cancel_at_period_end = False
    db.add(subscription)

    _record_status_change(
        db,
        subscription,
        to_status=SubscriptionStatus.ACTIVE.value,
        reason="Payment succeeded.",
        changed_by=None,
    )

    notify_user(
        db,
        user_id=subscription.user_id,
        notification_type=NotificationType.PAYMENT.value,
        title="Subscription active",
        body=f"Your {plan.name} subscription is active until {period_end:%Y-%m-%d}.",
        data={"subscription_id": str(subscription.id), "payment_id": str(payment.id)},
    )

    if is_first_activation:
        record_event(
            db,
            event_type=AnalyticsEventType.SUBSCRIPTION_STARTED.value,
            user_id=subscription.user_id,
            entity_type="subscription",
            entity_id=subscription.id,
            properties={"plan_slug": plan.slug, "billing_interval": plan.billing_interval},
        )


def handle_failed_subscription_payment(db: Session, payment: Payment) -> None:
    assert payment.subscription_id is not None
    subscription = db.get(Subscription, payment.subscription_id)
    assert subscription is not None

    if subscription.status == SubscriptionStatus.TRIALING.value:
        # Never successfully activated — nothing to protect with a grace
        # period.
        _record_status_change(
            db,
            subscription,
            to_status=SubscriptionStatus.EXPIRED.value,
            reason="Initial payment failed.",
            changed_by=None,
        )
    else:
        grace_days = get_settings().subscription_grace_period_days
        subscription.grace_period_ends_at = datetime.now(UTC) + timedelta(days=grace_days)
        db.add(subscription)
        _record_status_change(
            db,
            subscription,
            to_status=SubscriptionStatus.PAST_DUE.value,
            reason="Renewal payment failed.",
            changed_by=None,
        )

    notify_user(
        db,
        user_id=subscription.user_id,
        notification_type=NotificationType.PAYMENT.value,
        title="Subscription payment failed",
        body="We couldn't process your subscription payment. Please retry to keep your benefits.",
        data={"subscription_id": str(subscription.id), "payment_id": str(payment.id)},
    )


# --- Cancellation --------------------------------------------------------------


def cancel_subscription(
    db: Session, subscription: Subscription, *, cancelled_by: uuid.UUID, reason: str | None
) -> None:
    if subscription.status not in (
        SubscriptionStatus.ACTIVE.value,
        SubscriptionStatus.PAST_DUE.value,
        SubscriptionStatus.TRIALING.value,
    ):
        raise AppError("This subscription cannot be cancelled.", status_code=422)

    # Standard "cancel at period end" behavior: access continues through the
    # already-paid-for period; `status` itself doesn't change here (so no
    # SubscriptionStatusHistory row — it only logs actual status
    # transitions), only the flag that `process_due_subscriptions()` reads
    # once the period actually ends.
    subscription.cancel_at_period_end = True
    subscription.cancelled_at = datetime.now(UTC)
    db.add(subscription)

    _record_audit(
        db,
        actor_id=cancelled_by,
        action="subscription.cancelled",
        entity_type="subscriptions",
        entity_id=subscription.id,
        after_state={"reason": reason},
    )


# --- Expiration / grace-period foundation -------------------------------------


def process_due_subscriptions(db: Session, *, now: datetime | None = None) -> int:
    """See docs/subscriptions-and-entitlements.md#grace-period. No scheduler
    exists in this environment yet — this is invoked via
    `python -m app.cli.process_subscriptions`, mirroring
    `reconcile_pending_payments()`."""
    now = now or datetime.now(UTC)
    changed = 0

    ending = (
        db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.current_period_end <= now,
            )
        )
        .scalars()
        .all()
    )
    for subscription in ending:
        if subscription.cancel_at_period_end:
            _record_status_change(
                db,
                subscription,
                to_status=SubscriptionStatus.EXPIRED.value,
                reason="Cancelled at period end.",
                changed_by=None,
            )
        else:
            grace_days = get_settings().subscription_grace_period_days
            subscription.grace_period_ends_at = now + timedelta(days=grace_days)
            db.add(subscription)
            _record_status_change(
                db,
                subscription,
                to_status=SubscriptionStatus.PAST_DUE.value,
                reason="No renewal payment received by period end.",
                changed_by=None,
            )
        changed += 1

    overdue = (
        db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.PAST_DUE.value,
                Subscription.grace_period_ends_at.is_not(None),
                Subscription.grace_period_ends_at <= now,
            )
        )
        .scalars()
        .all()
    )
    for subscription in overdue:
        _record_status_change(
            db,
            subscription,
            to_status=SubscriptionStatus.EXPIRED.value,
            reason="Grace period elapsed with no successful renewal.",
            changed_by=None,
        )
        changed += 1

    return changed


# --- Billing / status history listings ----------------------------------------


def list_billing_history(db: Session, user_id: uuid.UUID) -> list[Payment]:
    return list(
        db.execute(
            select(Payment)
            .where(
                Payment.payer_id == user_id,
                Payment.payment_type == PaymentType.SUBSCRIPTION.value,
            )
            .order_by(Payment.created_at.desc())
        )
        .scalars()
        .all()
    )


def list_status_history(db: Session, subscription_id: uuid.UUID) -> list[SubscriptionStatusHistory]:
    return list(
        db.execute(
            select(SubscriptionStatusHistory)
            .where(SubscriptionStatusHistory.subscription_id == subscription_id)
            .order_by(SubscriptionStatusHistory.created_at.desc())
        )
        .scalars()
        .all()
    )
