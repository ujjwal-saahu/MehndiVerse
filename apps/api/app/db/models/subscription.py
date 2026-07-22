import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import (
    BillingInterval,
    SubscriptionStatus,
    SubscriptionTargetRole,
    check_in,
)
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class SubscriptionPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscription_plans"
    __table_args__ = (
        UniqueConstraint("name", name="uq_subscription_plans_name"),
        UniqueConstraint("slug", name="uq_subscription_plans_slug"),
        CheckConstraint(check_in("target_role", SubscriptionTargetRole), name="target_role_valid"),
        CheckConstraint(
            check_in("billing_interval", BillingInterval), name="billing_interval_valid"
        ),
        CheckConstraint("price_amount >= 0", name="price_amount_non_negative"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    target_role: Mapped[str] = mapped_column(String(20), nullable=False)
    price_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False)
    features: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(check_in("status", SubscriptionStatus), name="status_valid"),
        CheckConstraint("current_period_end > current_period_start", name="period_end_after_start"),
        UniqueConstraint(
            "provider_subscription_id", name="uq_subscriptions_provider_subscription_id"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SubscriptionStatus.TRIALING.value
    )
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set when a renewal payment fails, moving status to `past_due` — see
    # docs/subscriptions-and-entitlements.md#grace-period. Entitlements stay
    # active until this passes; `process_due_subscriptions()` transitions
    # the subscription to `expired` once it does with no successful renewal.
    grace_period_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="subscriptions")


class SubscriptionStatusHistory(Base):
    """Append-only audit log of every subscription status transition. Never
    updated or deleted after insert — mirrors `BookingStatusHistory`
    (app/db/models/booking.py)."""

    __tablename__ = "subscription_status_history"
    __table_args__ = (
        CheckConstraint(
            f"from_status IS NULL OR {check_in('from_status', SubscriptionStatus)}",
            name="from_status_valid",
        ),
        CheckConstraint(check_in("to_status", SubscriptionStatus), name="to_status_valid"),
        Index("ix_subscription_status_history_subscription_id", "subscription_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="RESTRICT"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
