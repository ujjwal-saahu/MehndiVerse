"""one conversation per booking

Adds a uniqueness guarantee at the database level for "one conversation per
booking" (Phase 14): `conversations.booking_id` gets a UNIQUE constraint.
Postgres treats multiple NULLs as distinct, so `inquiry`/`support`
conversations (which don't set `booking_id`) are unaffected — only `booking`
type conversations, which always set it, are constrained to at most one row
per booking. See docs/booking-messaging.md.

Revision ID: f3d8b6a1c9e4
Revises: c4a927f6e1b8
Create Date: 2026-07-26 09:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3d8b6a1c9e4"
down_revision: str | Sequence[str] | None = "c4a927f6e1b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        op.f("uq_conversations_booking_id"), "conversations", ["booking_id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_conversations_booking_id"), "conversations", type_="unique")
