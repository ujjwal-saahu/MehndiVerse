import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import CouponDiscountType, check_in
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Coupon(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "coupons"
    __table_args__ = (
        UniqueConstraint("code", name="uq_coupons_code"),
        CheckConstraint(check_in("discount_type", CouponDiscountType), name="discount_type_valid"),
        CheckConstraint("discount_value > 0", name="discount_value_positive"),
        CheckConstraint("redemption_count >= 0", name="redemption_count_non_negative"),
        CheckConstraint(
            "max_redemptions IS NULL OR max_redemptions > 0", name="max_redemptions_positive"
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > valid_from", name="valid_until_after_valid_from"
        ),
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(3))
    max_redemptions: Mapped[int | None] = mapped_column()
    redemption_count: Mapped[int] = mapped_column(default=0, nullable=False)
    min_booking_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    redemptions: Mapped[list["CouponRedemption"]] = relationship(back_populates="coupon")


class CouponRedemption(UUIDPrimaryKeyMixin, Base):
    """No updated_at: a redemption is an immutable fact once recorded."""

    __tablename__ = "coupon_redemptions"
    __table_args__ = (
        UniqueConstraint("coupon_id", "user_id", name="uq_coupon_redemptions_coupon_user"),
        CheckConstraint("discount_applied > 0", name="discount_applied_positive"),
    )

    coupon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coupons.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="RESTRICT")
    )
    # Nullable, parallel to booking_id — a coupon redemption is attributed to
    # whichever checkout it was applied against (see
    # docs/subscriptions-and-entitlements.md#coupons-and-subscription-checkout).
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="RESTRICT")
    )
    discount_applied: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    redeemed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    coupon: Mapped["Coupon"] = relationship(back_populates="redemptions")
