import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import PaymentStatus, PaymentType, PayoutStatus, RefundStatus, check_in
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Payments, refunds, payouts, and artist earnings are financial records:
# never soft-deleted, never hard-deleted, and every FK to them (or from them
# to users/bookings) uses RESTRICT so a row can never vanish as a side
# effect of deleting something else. See docs/payments.md#7 and
# docs/database-schema.md#financial-data-integrity.
#
# All money columns are Integer *minor currency units* (e.g. paise, not
# rupees) — see docs/payments.md#7-integer-minor-currency-units. Never a
# float/Decimal major-unit amount: minor-unit integers are exact and match
# what every payment provider's API actually speaks (Razorpay's `amount` is
# paise).


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """`provider_order_id` is known the moment we ask the provider to create
    an order (before the customer has paid anything); `provider_payment_id`
    is only known once a webhook or reconciliation poll confirms an actual
    payment attempt against that order — see
    docs/payments.md#3-payment-order-creation. `idempotency_key` lets a
    retried "create order" request return the same row instead of creating a
    duplicate order — see docs/payments.md#6-idempotency-keys."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(check_in("status", PaymentStatus), name="status_valid"),
        CheckConstraint(check_in("payment_type", PaymentType), name="payment_type_valid"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "commission_amount IS NULL OR commission_amount >= 0",
            name="commission_amount_non_negative",
        ),
        CheckConstraint("net_amount IS NULL OR net_amount >= 0", name="net_amount_non_negative"),
        UniqueConstraint("provider_payment_id", name="uq_payments_provider_payment_id"),
        UniqueConstraint("provider_order_id", name="uq_payments_provider_order_id"),
        UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
        # Exactly one parent: a payment is either a booking charge or a
        # subscription charge, never both and never neither — see
        # docs/subscriptions-and-entitlements.md#subscription-checkout-reuses-
        # payments.
        CheckConstraint(
            "(booking_id IS NOT NULL AND subscription_id IS NULL) OR "
            "(booking_id IS NULL AND subscription_id IS NOT NULL)",
            name="exactly_one_parent",
        ),
    )

    # Nullable — see the `exactly_one_parent` check constraint below.
    # Non-null for a booking payment (deposit/balance/full); null for a
    # subscription payment, which sets subscription_id instead.
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        index=True,
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="RESTRICT"),
        index=True,
    )
    payer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_order_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255))
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PaymentStatus.PENDING.value, index=True
    )
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    # Set once the payment succeeds — see
    # docs/payments.md#8-platform-commission-and-artist-earnings.
    # commission_amount + net_amount == amount.
    commission_amount: Mapped[int | None] = mapped_column(Integer)
    net_amount: Mapped[int | None] = mapped_column(Integer)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # passive_deletes=True: refunds/earning use ON DELETE RESTRICT — let
    # Postgres enforce the restriction rather than the ORM nulling the FK.
    refunds: Mapped[list["Refund"]] = relationship(back_populates="payment", passive_deletes=True)
    earning: Mapped["ArtistEarning | None"] = relationship(
        back_populates="payment", passive_deletes=True
    )


class Refund(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "refunds"
    __table_args__ = (
        CheckConstraint(check_in("status", RefundStatus), name="status_valid"),
        CheckConstraint("amount > 0", name="amount_positive"),
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RefundStatus.PENDING.value
    )
    processed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    provider_refund_id: Mapped[str | None] = mapped_column(String(255))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    payment: Mapped["Payment"] = relationship(back_populates="refunds")


class Payout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Payout-record **foundation** — see
    docs/payments.md#9-payout-record-foundation. Represents a batch of the
    artist's accumulated `ArtistEarning` rows being marked ready for
    transfer; this phase does not execute an actual bank transfer, only the
    record-keeping a future payouts phase would drive."""

    __tablename__ = "payouts"
    __table_args__ = (
        CheckConstraint(check_in("status", PayoutStatus), name="status_valid"),
        CheckConstraint("amount > 0", name="amount_positive"),
    )

    artist_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artist_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="RESTRICT")
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PayoutStatus.PENDING.value
    )
    provider_payout_id: Mapped[str | None] = mapped_column(String(255))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    earnings: Mapped[list["ArtistEarning"]] = relationship(back_populates="payout")


class ArtistEarning(UUIDPrimaryKeyMixin, Base):
    """The artist's share of one successful `Payment`, after platform
    commission — see docs/payments.md#8-platform-commission-and-artist-
    earnings. Exactly one earning per payment (`payment_id` is unique): a
    payment either earns the artist money once, or it doesn't. `payout_id`
    is set once this earning has been included in a `Payout` batch — see
    docs/payments.md#9-payout-record-foundation."""

    __tablename__ = "artist_earnings"
    __table_args__ = (
        CheckConstraint("gross_amount > 0", name="gross_amount_positive"),
        CheckConstraint("commission_amount >= 0", name="commission_amount_non_negative"),
        CheckConstraint("net_amount >= 0", name="net_amount_non_negative"),
        UniqueConstraint("payment_id", name="uq_artist_earnings_payment_id"),
    )

    artist_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artist_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    gross_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    commission_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    net_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    payout_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payouts.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    payment: Mapped["Payment"] = relationship(back_populates="earning")
    payout: Mapped["Payout | None"] = relationship(back_populates="earnings")


class PaymentWebhookEvent(Base):
    """Idempotent webhook-processing ledger — see
    docs/payments.md#5-signed-webhook-handling-and-duplicate-protection. The
    unique constraint on (provider, event_type, provider_reference) is what
    actually prevents a replayed webhook delivery from being processed
    twice: the second insert attempt fails uniqueness, and the caller
    treats that as "already handled" rather than reprocessing."""

    __tablename__ = "payment_webhook_events"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "event_type",
            "provider_reference",
            name="uq_payment_webhook_events_provider_event_type_reference",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
