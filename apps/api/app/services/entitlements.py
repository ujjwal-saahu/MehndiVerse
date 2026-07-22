"""Central entitlement/quota enforcement — see
docs/subscriptions-and-entitlements.md#feature-entitlements-and-usage-
quotas.

Every check here re-derives the caller's plan and usage from the database;
nothing is ever trusted from the client (no "am I premium?" flag on a
request body is ever honored) — the backend is the only place an
entitlement can be granted or denied. Route handlers call these functions
directly rather than relying on the frontend to hide a button.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.enums import SubscriptionStatus, UserRole
from app.db.models.subscription import Subscription, SubscriptionPlan
from app.db.models.usage import UsageRecord
from app.db.models.user import User

# Fallback feature bags for a user with no subscription row at all — mirror
# the seeded free plans (migrations/versions/f1c8a37e5b04_seed_subscription_
# plans.py) so "never subscribed" and "on the free plan" behave identically
# without every call site special-casing a missing row.
_DEFAULT_CUSTOMER_FEATURES: dict[str, Any] = {
    "premium_design_access": False,
    "download_limit_per_month": 5,
    "ai_credits_per_month": 3,
}
_DEFAULT_ARTIST_FEATURES: dict[str, Any] = {
    "portfolio_limit": 10,
    "download_limit_per_month": 5,
    "ai_credits_per_month": 3,
}

# `past_due` (grace period) still grants entitlements — see
# docs/subscriptions-and-entitlements.md#grace-period.
_ENTITLED_STATUSES = frozenset({SubscriptionStatus.ACTIVE.value, SubscriptionStatus.PAST_DUE.value})


def get_active_subscription(db: Session, user_id: uuid.UUID) -> Subscription | None:
    return (
        db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.status.in_(_ENTITLED_STATUSES))
            .order_by(Subscription.current_period_end.desc())
        )
        .scalars()
        .first()
    )


def get_effective_features(db: Session, user: User) -> dict[str, Any]:
    """The feature bag that applies to this user right now."""
    subscription = get_active_subscription(db, user.id)
    if subscription is not None:
        plan = db.get(SubscriptionPlan, subscription.plan_id)
        assert plan is not None
        return plan.features or {}
    if user.role == UserRole.ARTIST.value:
        return _DEFAULT_ARTIST_FEATURES
    return _DEFAULT_CUSTOMER_FEATURES


def _period_bounds(now: datetime) -> tuple[datetime, datetime]:
    """Calendar-month usage window — independent of any subscription's own
    billing anchor date, so a free-tier user (no subscription row at all)
    still gets a well-defined monthly quota."""
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (
        start.replace(year=start.year + 1, month=1)
        if start.month == 12
        else start.replace(month=start.month + 1)
    )
    return start, end


def get_usage_count(
    db: Session, *, user_id: uuid.UUID, usage_type: str, now: datetime | None = None
) -> int:
    now = now or datetime.now(UTC)
    period_start, _ = _period_bounds(now)
    record = db.execute(
        select(UsageRecord).where(
            UsageRecord.user_id == user_id,
            UsageRecord.usage_type == usage_type,
            UsageRecord.period_start == period_start,
        )
    ).scalar_one_or_none()
    return record.count if record is not None else 0


def check_and_increment_usage(
    db: Session, *, user: User, usage_type: str, limit_key: str, now: datetime | None = None
) -> None:
    """Raises if the user is already at their plan's quota for this usage
    type this period; otherwise increments (creating the period's row on
    first use) so the caller may proceed. Must run in the same transaction
    as the action it gates — a later rollback undoes the increment along
    with everything else."""
    now = now or datetime.now(UTC)
    features = get_effective_features(db, user)
    limit = features.get(limit_key)
    if limit is None:
        return  # No numeric cap for this feature on the user's plan (e.g. unlimited).

    period_start, period_end = _period_bounds(now)
    record = db.execute(
        select(UsageRecord).where(
            UsageRecord.user_id == user.id,
            UsageRecord.usage_type == usage_type,
            UsageRecord.period_start == period_start,
        )
    ).scalar_one_or_none()
    current = record.count if record is not None else 0
    if current >= limit:
        raise AppError(
            "You've reached your plan's limit for this feature this month. Upgrade your "
            "plan for a higher limit.",
            status_code=403,
        )

    if record is None:
        db.add(
            UsageRecord(
                user_id=user.id,
                usage_type=usage_type,
                period_start=period_start,
                period_end=period_end,
                count=1,
            )
        )
    else:
        record.count = current + 1
        db.add(record)


def require_premium_design_access(db: Session, user: User) -> None:
    features = get_effective_features(db, user)
    if not features.get("premium_design_access", False):
        raise AppError("This design is only available to premium subscribers.", status_code=403)


def require_portfolio_capacity(db: Session, user: User, *, current_design_count: int) -> None:
    features = get_effective_features(db, user)
    limit = features.get("portfolio_limit")
    if limit is not None and current_design_count >= limit:
        raise AppError(
            "You've reached your plan's portfolio limit. Upgrade to publish more designs.",
            status_code=403,
        )
