"""artist availability and scheduling

Adds timezone + default buffer settings to `artist_profiles`, per-service
buffer/travel-buffer overrides to `artist_services`, and extends
`artist_blocked_dates` with a `block_type` (holiday/personal_leave/vacation/
other — all four share one table) and an optional `start_time`/`end_time`
pair so the same table covers both whole-day blocks (holidays, vacation,
leave) and a specific-hours "manual schedule block" within a single day. See
docs/artist-scheduling.md.

Revision ID: 0eab3947e802
Revises: de1b95efd1f0
Create Date: 2026-07-19 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0eab3947e802"
down_revision: str | Sequence[str] | None = "de1b95efd1f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- artist_profiles: timezone + default buffers ------------------------
    op.add_column(
        "artist_profiles",
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
    )
    op.add_column(
        "artist_profiles",
        sa.Column("default_buffer_minutes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "artist_profiles",
        sa.Column(
            "default_travel_buffer_minutes", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.create_check_constraint(
        op.f("ck_artist_profiles_default_buffer_minutes_non_negative"),
        "artist_profiles",
        "default_buffer_minutes >= 0",
    )
    op.create_check_constraint(
        op.f("ck_artist_profiles_default_travel_buffer_minutes_non_negative"),
        "artist_profiles",
        "default_travel_buffer_minutes >= 0",
    )

    # --- artist_services: per-service buffer overrides -----------------------
    op.add_column("artist_services", sa.Column("buffer_minutes", sa.Integer(), nullable=True))
    op.add_column(
        "artist_services", sa.Column("travel_buffer_minutes", sa.Integer(), nullable=True)
    )
    op.create_check_constraint(
        op.f("ck_artist_services_buffer_minutes_non_negative"),
        "artist_services",
        "buffer_minutes IS NULL OR buffer_minutes >= 0",
    )
    op.create_check_constraint(
        op.f("ck_artist_services_travel_buffer_minutes_non_negative"),
        "artist_services",
        "travel_buffer_minutes IS NULL OR travel_buffer_minutes >= 0",
    )

    # --- artist_blocked_dates: block_type + optional time-of-day range -------
    op.add_column(
        "artist_blocked_dates",
        sa.Column("block_type", sa.String(20), nullable=False, server_default="other"),
    )
    op.add_column("artist_blocked_dates", sa.Column("start_time", sa.Time(), nullable=True))
    op.add_column("artist_blocked_dates", sa.Column("end_time", sa.Time(), nullable=True))
    op.create_check_constraint(
        op.f("ck_artist_blocked_dates_block_type_valid"),
        "artist_blocked_dates",
        "block_type IN ('holiday', 'personal_leave', 'vacation', 'other')",
    )
    op.create_check_constraint(
        op.f("ck_artist_blocked_dates_time_range_consistent"),
        "artist_blocked_dates",
        "(start_time IS NULL AND end_time IS NULL) OR "
        "(start_time IS NOT NULL AND end_time IS NOT NULL AND end_time > start_time "
        "AND start_date = end_date)",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_artist_blocked_dates_time_range_consistent"),
        "artist_blocked_dates",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_artist_blocked_dates_block_type_valid"), "artist_blocked_dates", type_="check"
    )
    op.drop_column("artist_blocked_dates", "end_time")
    op.drop_column("artist_blocked_dates", "start_time")
    op.drop_column("artist_blocked_dates", "block_type")

    op.drop_constraint(
        op.f("ck_artist_services_travel_buffer_minutes_non_negative"),
        "artist_services",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_artist_services_buffer_minutes_non_negative"), "artist_services", type_="check"
    )
    op.drop_column("artist_services", "travel_buffer_minutes")
    op.drop_column("artist_services", "buffer_minutes")

    op.drop_constraint(
        op.f("ck_artist_profiles_default_travel_buffer_minutes_non_negative"),
        "artist_profiles",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_artist_profiles_default_buffer_minutes_non_negative"),
        "artist_profiles",
        type_="check",
    )
    op.drop_column("artist_profiles", "default_travel_buffer_minutes")
    op.drop_column("artist_profiles", "default_buffer_minutes")
    op.drop_column("artist_profiles", "timezone")
