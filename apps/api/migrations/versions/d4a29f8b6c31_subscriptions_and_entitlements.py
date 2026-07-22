"""subscriptions and entitlements

Phase 18. `payments.booking_id` becomes nullable and `payments` gains a
`subscription_id` column so a subscription checkout can settle through the
exact same order/webhook/reconciliation machinery a booking payment does
(see docs/subscriptions-and-entitlements.md#subscription-checkout-reuses-
payments) — a new `exactly_one_parent` check constraint keeps every payment
attributed to exactly one of the two. `subscriptions` gains
`grace_period_ends_at` for the failed-renewal grace period (reusing the
existing `past_due` status rather than adding a new enum value).
`coupon_redemptions` gains a `subscription_id` column, parallel to the
existing nullable `booking_id`, so a coupon can be redeemed against either
kind of checkout. Two new tables: `subscription_status_history` (mirrors
`booking_status_history`) and `usage_records` (per-user, per-billing-period
counters backing download/AI-credit quotas).

Revision ID: d4a29f8b6c31
Revises: 7a448a982206
Create Date: 2026-07-20 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a29f8b6c31"
down_revision: str | Sequence[str] | None = "7a448a982206"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- payments: nullable booking_id + subscription_id parent ------------
    op.alter_column("payments", "booking_id", existing_type=postgresql.UUID(), nullable=True)
    op.add_column("payments", sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        op.f("fk_payments_subscription_id_subscriptions"),
        "payments",
        "subscriptions",
        ["subscription_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_payments_subscription_id"), "payments", ["subscription_id"], unique=False
    )
    op.drop_constraint(op.f("ck_payments_payment_type_valid"), "payments", type_="check")
    op.create_check_constraint(
        op.f("ck_payments_payment_type_valid"),
        "payments",
        "payment_type IN ('deposit', 'balance', 'full', 'subscription')",
    )
    op.create_check_constraint(
        op.f("ck_payments_exactly_one_parent"),
        "payments",
        "(booking_id IS NOT NULL AND subscription_id IS NULL) OR "
        "(booking_id IS NULL AND subscription_id IS NOT NULL)",
    )

    # --- subscriptions: grace period ----------------------------------------
    op.add_column(
        "subscriptions", sa.Column("grace_period_ends_at", sa.DateTime(timezone=True), nullable=True)
    )

    # --- subscription_status_history: mirrors booking_status_history -------
    op.create_table(
        "subscription_status_history",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "from_status IS NULL OR from_status IN "
            "('active', 'cancelled', 'expired', 'past_due', 'trialing')",
            name=op.f("ck_subscription_status_history_from_status_valid"),
        ),
        sa.CheckConstraint(
            "to_status IN ('active', 'cancelled', 'expired', 'past_due', 'trialing')",
            name=op.f("ck_subscription_status_history_to_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"],
            name=op.f("fk_subscription_status_history_subscription_id_subscriptions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"], ["users.id"],
            name=op.f("fk_subscription_status_history_changed_by_users"), ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscription_status_history")),
    )
    op.create_index(
        "ix_subscription_status_history_subscription_id",
        "subscription_status_history",
        ["subscription_id"],
    )

    # --- coupon_redemptions: subscription_id, parallel to booking_id -------
    op.add_column(
        "coupon_redemptions", sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_coupon_redemptions_subscription_id_subscriptions"),
        "coupon_redemptions",
        "subscriptions",
        ["subscription_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # --- usage_records: per-user, per-period quota counters -----------------
    op.create_table(
        "usage_records",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usage_type", sa.String(length=30), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "usage_type IN ('design_download', 'ai_generation')",
            name=op.f("ck_usage_records_usage_type_valid"),
        ),
        sa.CheckConstraint("count >= 0", name=op.f("ck_usage_records_count_non_negative")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_usage_records_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_records")),
        sa.UniqueConstraint(
            "user_id", "usage_type", "period_start",
            name="uq_usage_records_user_type_period",
        ),
    )
    op.create_index("ix_usage_records_user_id", "usage_records", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_usage_records_user_id", table_name="usage_records")
    op.drop_table("usage_records")

    op.drop_constraint(
        op.f("fk_coupon_redemptions_subscription_id_subscriptions"),
        "coupon_redemptions",
        type_="foreignkey",
    )
    op.drop_column("coupon_redemptions", "subscription_id")

    op.drop_index(
        "ix_subscription_status_history_subscription_id",
        table_name="subscription_status_history",
    )
    op.drop_table("subscription_status_history")

    op.drop_column("subscriptions", "grace_period_ends_at")

    op.drop_constraint(op.f("ck_payments_exactly_one_parent"), "payments", type_="check")
    op.drop_constraint(op.f("ck_payments_payment_type_valid"), "payments", type_="check")
    op.create_check_constraint(
        op.f("ck_payments_payment_type_valid"),
        "payments",
        "payment_type IN ('deposit', 'balance', 'full')",
    )
    op.drop_index(op.f("ix_payments_subscription_id"), table_name="payments")
    op.drop_constraint(
        op.f("fk_payments_subscription_id_subscriptions"), "payments", type_="foreignkey"
    )
    op.drop_column("payments", "subscription_id")
    op.alter_column("payments", "booking_id", existing_type=postgresql.UUID(), nullable=False)
