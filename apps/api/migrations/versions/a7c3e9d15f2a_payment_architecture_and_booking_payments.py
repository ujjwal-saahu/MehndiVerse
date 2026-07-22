"""payment architecture and booking payments

Phase 15. `payments.amount`/`refunds.amount`/`payouts.amount` move from
`Numeric(12,2)` (major currency units, e.g. rupees) to `Integer` (minor
currency units, e.g. paise) — see docs/payments.md#7-integer-minor-currency-
units. `payments` gains `provider_order_id` (known at order-creation time,
distinct from `provider_payment_id` which is only known once a webhook or
reconciliation confirms the payment), `idempotency_key`, and
`commission_amount`/`net_amount`. Two new tables: `payment_webhook_events`
(idempotent webhook processing ledger) and `artist_earnings` (the
artist's share of a successful payment after platform commission).

Revision ID: a7c3e9d15f2a
Revises: f3d8b6a1c9e4
Create Date: 2026-08-02 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c3e9d15f2a"
down_revision: str | Sequence[str] | None = "f3d8b6a1c9e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- payments: minor units + order/payment id split + idempotency ------
    op.alter_column(
        "payments",
        "amount",
        type_=sa.Integer(),
        postgresql_using="(amount * 100)::integer",
    )
    op.alter_column("payments", "provider_payment_id", existing_type=sa.String(255), nullable=True)
    op.add_column(
        "payments", sa.Column("provider_order_id", sa.String(255), nullable=False, server_default="")
    )
    op.alter_column("payments", "provider_order_id", server_default=None)
    op.create_unique_constraint(
        op.f("uq_payments_provider_order_id"), "payments", ["provider_order_id"]
    )
    op.add_column("payments", sa.Column("idempotency_key", sa.String(255), nullable=True))
    op.create_unique_constraint(
        op.f("uq_payments_idempotency_key"), "payments", ["idempotency_key"]
    )
    op.add_column("payments", sa.Column("commission_amount", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("net_amount", sa.Integer(), nullable=True))
    op.create_check_constraint(
        op.f("ck_payments_commission_amount_non_negative"),
        "payments",
        "commission_amount IS NULL OR commission_amount >= 0",
    )
    op.create_check_constraint(
        op.f("ck_payments_net_amount_non_negative"),
        "payments",
        "net_amount IS NULL OR net_amount >= 0",
    )

    # --- refunds / payouts: minor units --------------------------------------
    op.alter_column(
        "refunds", "amount", type_=sa.Integer(), postgresql_using="(amount * 100)::integer"
    )
    op.alter_column(
        "payouts", "amount", type_=sa.Integer(), postgresql_using="(amount * 100)::integer"
    )

    # --- payment_webhook_events: idempotent webhook processing ledger -------
    op.create_table(
        "payment_webhook_events",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("provider_reference", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "provider", "event_type", "provider_reference",
            name=op.f("uq_payment_webhook_events_provider_event_type_reference"),
        ),
    )

    # --- artist_earnings: the artist's share after commission ----------------
    op.create_table(
        "artist_earnings",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "artist_profile_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gross_amount", sa.Integer(), nullable=False),
        sa.Column("commission_amount", sa.Integer(), nullable=False),
        sa.Column("net_amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("payout_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["artist_profile_id"], ["artist_profiles.id"],
            name=op.f("fk_artist_earnings_artist_profile_id_artist_profiles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["bookings.id"],
            name=op.f("fk_artist_earnings_booking_id_bookings"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"], ["payments.id"],
            name=op.f("fk_artist_earnings_payment_id_payments"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payout_id"], ["payouts.id"],
            name=op.f("fk_artist_earnings_payout_id_payouts"), ondelete="SET NULL",
        ),
        sa.UniqueConstraint("payment_id", name=op.f("uq_artist_earnings_payment_id")),
        sa.CheckConstraint("gross_amount > 0", name=op.f("ck_artist_earnings_gross_amount_positive")),
        sa.CheckConstraint(
            "commission_amount >= 0", name=op.f("ck_artist_earnings_commission_amount_non_negative")
        ),
        sa.CheckConstraint(
            "net_amount >= 0", name=op.f("ck_artist_earnings_net_amount_non_negative")
        ),
    )
    op.create_index(
        "ix_artist_earnings_artist_profile_id", "artist_earnings", ["artist_profile_id"]
    )
    op.create_index("ix_artist_earnings_booking_id", "artist_earnings", ["booking_id"])
    op.create_index("ix_artist_earnings_payout_id", "artist_earnings", ["payout_id"])


def downgrade() -> None:
    op.drop_index("ix_artist_earnings_payout_id", table_name="artist_earnings")
    op.drop_index("ix_artist_earnings_booking_id", table_name="artist_earnings")
    op.drop_index("ix_artist_earnings_artist_profile_id", table_name="artist_earnings")
    op.drop_table("artist_earnings")
    op.drop_table("payment_webhook_events")

    op.alter_column(
        "payouts", "amount", type_=sa.Numeric(12, 2), postgresql_using="(amount::numeric / 100)"
    )
    op.alter_column(
        "refunds", "amount", type_=sa.Numeric(12, 2), postgresql_using="(amount::numeric / 100)"
    )

    op.drop_constraint(op.f("ck_payments_net_amount_non_negative"), "payments", type_="check")
    op.drop_constraint(
        op.f("ck_payments_commission_amount_non_negative"), "payments", type_="check"
    )
    op.drop_column("payments", "net_amount")
    op.drop_column("payments", "commission_amount")
    op.drop_constraint(op.f("uq_payments_idempotency_key"), "payments", type_="unique")
    op.drop_column("payments", "idempotency_key")
    op.drop_constraint(op.f("uq_payments_provider_order_id"), "payments", type_="unique")
    op.drop_column("payments", "provider_order_id")
    op.alter_column("payments", "provider_payment_id", existing_type=sa.String(255), nullable=False)
    op.alter_column(
        "payments", "amount", type_=sa.Numeric(12, 2), postgresql_using="(amount::numeric / 100)"
    )
