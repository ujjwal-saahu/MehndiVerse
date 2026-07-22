"""booking system without payments

Replaces the Phase 2 placeholder 8-status booking lifecycle with the full
15-status state machine (draft/requested/artist_reviewing/quotation_sent/
customer_reviewing/confirmed/deposit_pending/deposit_paid/in_progress/
completed/cancelled/rejected/refund_requested/refunded/disputed) and adds the
booking-request fields collected while drafting a request (event type,
number of customers, design preferences, budget range, contact details).
`requested_date`/`location_type` become nullable since a draft may not have
decided these yet — they're required only at submission (see
app/services/booking.py). Payments remain disabled this phase: the
deposit_pending/deposit_paid/refund_requested/refunded states exist in the
graph for a later payments phase to wire up, but nothing in this phase
reaches them through an HTTP endpoint. See docs/booking-lifecycle.md.

Revision ID: c4a927f6e1b8
Revises: 0eab3947e802
Create Date: 2026-07-19 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4a927f6e1b8"
down_revision: str | Sequence[str] | None = "0eab3947e802"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_BOOKING_STATUSES = (
    "draft",
    "requested",
    "artist_reviewing",
    "quotation_sent",
    "customer_reviewing",
    "confirmed",
    "deposit_pending",
    "deposit_paid",
    "in_progress",
    "completed",
    "cancelled",
    "rejected",
    "refund_requested",
    "refunded",
    "disputed",
)

_OLD_BOOKING_STATUSES = (
    "requested",
    "quoted",
    "confirmed",
    "completed",
    "cancelled",
    "disputed",
    "declined",
    "expired",
)

_EVENT_TYPES = (
    "wedding",
    "engagement",
    "festival",
    "baby_shower",
    "party",
    "corporate_event",
    "other",
)

# Old rows (if any exist in a dev database) are remapped onto their closest
# equivalent in the new vocabulary rather than left dangling — "quoted" and
# "declined" have direct new-world analogues; "expired" (an un-actioned
# quotation) is remapped to "cancelled", the closest terminal equivalent
# since the new graph has no bare "expired" booking status.
_STATUS_REMAP_UP = {
    "quoted": "quotation_sent",
    "declined": "rejected",
    "expired": "cancelled",
}
_STATUS_REMAP_DOWN = {
    "artist_reviewing": "requested",
    "quotation_sent": "quoted",
    "customer_reviewing": "quoted",
    "deposit_pending": "confirmed",
    "deposit_paid": "confirmed",
    "in_progress": "confirmed",
    "rejected": "declined",
    "refund_requested": "completed",
    "refunded": "completed",
    "draft": "requested",
}


def upgrade() -> None:
    op.drop_constraint(op.f("ck_bookings_status_valid"), "bookings", type_="check")
    op.drop_constraint(
        op.f("ck_booking_status_history_from_status_valid"), "booking_status_history", type_="check"
    )
    op.drop_constraint(
        op.f("ck_booking_status_history_to_status_valid"), "booking_status_history", type_="check"
    )

    bookings = sa.table("bookings", sa.column("status", sa.String))
    history = sa.table(
        "booking_status_history",
        sa.column("from_status", sa.String),
        sa.column("to_status", sa.String),
    )
    for old_value, new_value in _STATUS_REMAP_UP.items():
        op.execute(bookings.update().where(bookings.c.status == old_value).values(status=new_value))
        op.execute(
            history.update().where(history.c.from_status == old_value).values(from_status=new_value)
        )
        op.execute(
            history.update().where(history.c.to_status == old_value).values(to_status=new_value)
        )

    new_status_list = ", ".join(f"'{s}'" for s in _NEW_BOOKING_STATUSES)
    op.create_check_constraint(
        op.f("ck_bookings_status_valid"), "bookings", f"status IN ({new_status_list})"
    )
    op.create_check_constraint(
        op.f("ck_booking_status_history_from_status_valid"),
        "booking_status_history",
        f"from_status IS NULL OR from_status IN ({new_status_list})",
    )
    op.create_check_constraint(
        op.f("ck_booking_status_history_to_status_valid"),
        "booking_status_history",
        f"to_status IN ({new_status_list})",
    )

    # A draft booking may not have decided these yet — required only at
    # submission (see app/services/booking.py::missing_submission_requirements).
    op.alter_column("bookings", "requested_date", existing_type=sa.Date(), nullable=True)
    op.alter_column("bookings", "location_type", existing_type=sa.String(30), nullable=True)

    op.add_column("bookings", sa.Column("event_type", sa.String(30), nullable=True))
    op.add_column("bookings", sa.Column("num_customers", sa.Integer(), nullable=True))
    op.add_column("bookings", sa.Column("design_preferences", sa.Text(), nullable=True))
    op.add_column("bookings", sa.Column("budget_min", sa.Numeric(10, 2), nullable=True))
    op.add_column("bookings", sa.Column("budget_max", sa.Numeric(10, 2), nullable=True))
    op.add_column("bookings", sa.Column("contact_name", sa.String(150), nullable=True))
    op.add_column("bookings", sa.Column("contact_email", sa.String(255), nullable=True))
    op.add_column("bookings", sa.Column("contact_phone", sa.String(30), nullable=True))

    event_type_list = ", ".join(f"'{t}'" for t in _EVENT_TYPES)
    op.create_check_constraint(
        op.f("ck_bookings_event_type_valid"),
        "bookings",
        f"event_type IS NULL OR event_type IN ({event_type_list})",
    )
    op.create_check_constraint(
        op.f("ck_bookings_num_customers_positive"),
        "bookings",
        "num_customers IS NULL OR num_customers > 0",
    )
    op.create_check_constraint(
        op.f("ck_bookings_budget_min_non_negative"),
        "bookings",
        "budget_min IS NULL OR budget_min >= 0",
    )
    op.create_check_constraint(
        op.f("ck_bookings_budget_max_gte_budget_min"),
        "bookings",
        "budget_max IS NULL OR budget_min IS NULL OR budget_max >= budget_min",
    )

    op.create_index(
        "ix_bookings_artist_profile_id_status_requested_date",
        "bookings",
        ["artist_profile_id", "status", "requested_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_bookings_artist_profile_id_status_requested_date", table_name="bookings")

    op.drop_constraint(op.f("ck_bookings_budget_max_gte_budget_min"), "bookings", type_="check")
    op.drop_constraint(op.f("ck_bookings_budget_min_non_negative"), "bookings", type_="check")
    op.drop_constraint(op.f("ck_bookings_num_customers_positive"), "bookings", type_="check")
    op.drop_constraint(op.f("ck_bookings_event_type_valid"), "bookings", type_="check")

    op.drop_column("bookings", "contact_phone")
    op.drop_column("bookings", "contact_email")
    op.drop_column("bookings", "contact_name")
    op.drop_column("bookings", "budget_max")
    op.drop_column("bookings", "budget_min")
    op.drop_column("bookings", "design_preferences")
    op.drop_column("bookings", "num_customers")
    op.drop_column("bookings", "event_type")

    op.drop_constraint(op.f("ck_bookings_status_valid"), "bookings", type_="check")
    op.drop_constraint(
        op.f("ck_booking_status_history_from_status_valid"), "booking_status_history", type_="check"
    )
    op.drop_constraint(
        op.f("ck_booking_status_history_to_status_valid"), "booking_status_history", type_="check"
    )

    bookings = sa.table("bookings", sa.column("status", sa.String))
    history = sa.table(
        "booking_status_history",
        sa.column("from_status", sa.String),
        sa.column("to_status", sa.String),
    )
    for new_value, old_value in _STATUS_REMAP_DOWN.items():
        op.execute(bookings.update().where(bookings.c.status == new_value).values(status=old_value))
        op.execute(
            history.update().where(history.c.from_status == new_value).values(from_status=old_value)
        )
        op.execute(
            history.update().where(history.c.to_status == new_value).values(to_status=old_value)
        )

    old_status_list = ", ".join(f"'{s}'" for s in _OLD_BOOKING_STATUSES)
    op.create_check_constraint(
        op.f("ck_bookings_status_valid"), "bookings", f"status IN ({old_status_list})"
    )
    op.create_check_constraint(
        op.f("ck_booking_status_history_from_status_valid"),
        "booking_status_history",
        f"from_status IS NULL OR from_status IN ({old_status_list})",
    )
    op.create_check_constraint(
        op.f("ck_booking_status_history_to_status_valid"),
        "booking_status_history",
        f"to_status IN ({old_status_list})",
    )

    op.alter_column("bookings", "location_type", existing_type=sa.String(30), nullable=False)
    op.alter_column("bookings", "requested_date", existing_type=sa.Date(), nullable=False)
