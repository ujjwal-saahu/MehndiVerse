"""artist directory, services, and follower count

Adds the remaining `artist_services` fields needed for a real booking-facing
service listing (customer_capacity, deposit_required/amount,
travel_charge_amount, cancellation_policy) — see
docs/artist-directory.md#services. Adds `artist_profiles.follower_count`, a
denormalized counter mirroring `designs.like_count`/`save_count`'s pattern,
atomically maintained by `app/services/artist_directory.py::follow_artist`/
`unfollow_artist` rather than a live COUNT() at read time.

Revision ID: de1b95efd1f0
Revises: fdb53cc36719
Create Date: 2026-07-18 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "de1b95efd1f0"
down_revision: Union[str, Sequence[str], None] = "fdb53cc36719"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("artist_services", sa.Column("customer_capacity", sa.Integer(), nullable=True))
    op.add_column(
        "artist_services",
        sa.Column("deposit_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("artist_services", sa.Column("deposit_amount", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "artist_services", sa.Column("travel_charge_amount", sa.Numeric(10, 2), nullable=True)
    )
    op.add_column("artist_services", sa.Column("cancellation_policy", sa.Text(), nullable=True))
    op.create_check_constraint(
        op.f("ck_artist_services_customer_capacity_positive"),
        "artist_services",
        "customer_capacity IS NULL OR customer_capacity > 0",
    )
    op.create_check_constraint(
        op.f("ck_artist_services_deposit_amount_non_negative"),
        "artist_services",
        "deposit_amount IS NULL OR deposit_amount >= 0",
    )
    op.create_check_constraint(
        op.f("ck_artist_services_travel_charge_amount_non_negative"),
        "artist_services",
        "travel_charge_amount IS NULL OR travel_charge_amount >= 0",
    )

    op.add_column(
        "artist_profiles",
        sa.Column("follower_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        op.f("ck_artist_profiles_follower_count_non_negative"),
        "artist_profiles",
        "follower_count >= 0",
    )
    op.create_index(
        op.f("ix_artist_profiles_verification_status_rating_average"),
        "artist_profiles",
        ["verification_status", "rating_average"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_artist_profiles_verification_status_rating_average"), table_name="artist_profiles"
    )
    op.drop_constraint(
        op.f("ck_artist_profiles_follower_count_non_negative"), "artist_profiles", type_="check"
    )
    op.drop_column("artist_profiles", "follower_count")

    op.drop_constraint(
        op.f("ck_artist_services_travel_charge_amount_non_negative"),
        "artist_services",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_artist_services_deposit_amount_non_negative"), "artist_services", type_="check"
    )
    op.drop_constraint(
        op.f("ck_artist_services_customer_capacity_positive"), "artist_services", type_="check"
    )
    op.drop_column("artist_services", "cancellation_policy")
    op.drop_column("artist_services", "travel_charge_amount")
    op.drop_column("artist_services", "deposit_amount")
    op.drop_column("artist_services", "deposit_required")
    op.drop_column("artist_services", "customer_capacity")
