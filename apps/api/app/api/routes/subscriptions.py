"""Customer/artist-facing subscription endpoints — see
docs/subscriptions-and-entitlements.md.

Checkout reuses the exact same order/webhook confirmation flow booking
payments use (see app/services/subscriptions.py) — nothing here ever marks
a subscription active directly; that only happens once
`POST /webhooks/payments/razorpay` confirms the payment (see
docs/payments.md#4-never-trust-client-reported-success).
"""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, limiter
from app.core.config import get_settings
from app.core.exceptions import AppError, AuthorizationError
from app.db.models.subscription import Subscription, SubscriptionPlan
from app.db.session import get_db_session
from app.schemas.subscription import (
    BillingHistoryItemOut,
    CancelSubscriptionRequest,
    CheckoutOut,
    CheckoutRequest,
    MySubscriptionOut,
    SubscriptionOut,
    SubscriptionPlanOut,
    SubscriptionStatusHistoryOut,
)
from app.services.entitlements import get_active_subscription, get_effective_features
from app.services.subscriptions import (
    cancel_subscription,
    create_subscription_checkout,
    list_billing_history,
    list_status_history,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _rate_limit() -> str:
    return get_settings().subscription_rate_limit


def _plan_out(plan: SubscriptionPlan) -> SubscriptionPlanOut:
    return SubscriptionPlanOut(
        id=plan.id,
        name=plan.name,
        slug=plan.slug,
        target_role=plan.target_role,
        price_amount=float(plan.price_amount),
        currency=plan.currency,
        billing_interval=plan.billing_interval,
        features=plan.features,
        is_active=plan.is_active,
    )


def _subscription_out(db: Session, subscription: Subscription) -> SubscriptionOut:
    plan = db.get(SubscriptionPlan, subscription.plan_id)
    assert plan is not None
    return SubscriptionOut(
        id=subscription.id,
        user_id=subscription.user_id,
        plan=_plan_out(plan),
        status=subscription.status,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        grace_period_ends_at=subscription.grace_period_ends_at,
        started_at=subscription.started_at,
        cancelled_at=subscription.cancelled_at,
    )


def _get_plan_or_404(db: Session, plan_id: uuid.UUID) -> SubscriptionPlan:
    plan = db.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise AppError("Plan not found.", status_code=404)
    return plan


def _get_owned_subscription_or_404(
    db: Session, subscription_id: uuid.UUID, current: AuthenticatedUser
) -> Subscription:
    subscription = db.get(Subscription, subscription_id)
    if subscription is None:
        raise AppError("Subscription not found.", status_code=404)
    if subscription.user_id != current.user.id:
        raise AuthorizationError("You do not have access to this subscription.")
    return subscription


@router.get("/plans", response_model=list[SubscriptionPlanOut])
def list_subscription_plans(db: Session = Depends(get_db_session)) -> list[SubscriptionPlanOut]:
    plans = (
        db.execute(
            select(SubscriptionPlan)
            .where(SubscriptionPlan.is_active.is_(True))
            .order_by(SubscriptionPlan.target_role.asc(), SubscriptionPlan.price_amount.asc())
        )
        .scalars()
        .all()
    )
    return [_plan_out(p) for p in plans]


@router.post("/checkout", response_model=CheckoutOut, status_code=201)
@limiter.limit(_rate_limit())
def checkout_subscription(
    request: Request,
    payload: CheckoutRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> CheckoutOut:
    plan = _get_plan_or_404(db, payload.plan_id)
    payment, provider_key_id = create_subscription_checkout(
        db,
        user=current.user,
        plan=plan,
        coupon_code=payload.coupon_code,
        idempotency_key=payload.idempotency_key,
    )
    db.commit()
    db.refresh(payment)
    return CheckoutOut(
        payment_id=payment.id,
        provider=payment.provider,
        provider_order_id=payment.provider_order_id,
        provider_key_id=provider_key_id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
    )


@router.get("/me", response_model=MySubscriptionOut)
def get_my_subscription(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> MySubscriptionOut:
    subscription = get_active_subscription(db, current.user.id)
    features = get_effective_features(db, current.user)
    return MySubscriptionOut(
        subscription=_subscription_out(db, subscription) if subscription is not None else None,
        entitlements=features,
    )


@router.post("/me/cancel", response_model=SubscriptionOut)
def cancel_my_subscription(
    payload: CancelSubscriptionRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SubscriptionOut:
    subscription = get_active_subscription(db, current.user.id)
    if subscription is None:
        raise AppError("You don't have an active subscription.", status_code=404)
    cancel_subscription(db, subscription, cancelled_by=current.user.id, reason=payload.reason)
    db.commit()
    db.refresh(subscription)
    return _subscription_out(db, subscription)


@router.get("/me/billing-history", response_model=list[BillingHistoryItemOut])
def get_my_billing_history(
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[BillingHistoryItemOut]:
    payments = list_billing_history(db, current.user.id)
    out = []
    for payment in payments:
        plan_name: str | None = None
        if payment.subscription_id is not None:
            subscription = db.get(Subscription, payment.subscription_id)
            if subscription is not None:
                plan = db.get(SubscriptionPlan, subscription.plan_id)
                plan_name = plan.name if plan is not None else None
        out.append(
            BillingHistoryItemOut(
                payment_id=payment.id,
                plan_name=plan_name,
                amount=payment.amount,
                currency=payment.currency,
                status=payment.status,
                failure_reason=payment.failure_reason,
                paid_at=payment.paid_at,
                created_at=payment.created_at,
            )
        )
    return out


@router.get("/{subscription_id}/status-history", response_model=list[SubscriptionStatusHistoryOut])
def get_subscription_status_history(
    subscription_id: uuid.UUID,
    current: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[SubscriptionStatusHistoryOut]:
    _get_owned_subscription_or_404(db, subscription_id, current)
    history = list_status_history(db, subscription_id)
    return [
        SubscriptionStatusHistoryOut(
            id=h.id,
            from_status=h.from_status,
            to_status=h.to_status,
            reason=h.reason,
            created_at=h.created_at,
        )
        for h in history
    ]
