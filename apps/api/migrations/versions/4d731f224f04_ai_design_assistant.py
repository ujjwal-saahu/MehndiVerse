"""ai design assistant

Phase 21. New `ai_design_requests` table: one row per structured-form
personalized-design generation request. `generation_id` is a one-to-one
link to `ai_generations` (Phase 20) — job status, provider/model metadata,
cost, latency, and human-review state all live there; this table only adds
the Phase 21-specific structured-form fields (style/occasion/body_placement/
difficulty_level/density/is_symmetric/pattern_elements/theme/
personalization_text/additional_instructions/allow_provider_training), the
constructed prompt, the generation result, retry tracking, and save/share
state. See docs/ai-design-assistant.md.

Revision ID: 4d731f224f04
Revises: b7e2f4a9c1d3
Create Date: 2026-07-21 12:20:40.962838

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4d731f224f04"
down_revision: str | Sequence[str] | None = "b7e2f4a9c1d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_design_requests",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("generation_id", sa.UUID(), nullable=False),
        sa.Column("style", sa.String(length=100), nullable=False),
        sa.Column("occasion", sa.String(length=30), nullable=False),
        sa.Column("body_placement", sa.String(length=20), nullable=False),
        sa.Column("difficulty_level", sa.String(length=20), nullable=False),
        sa.Column("density", sa.String(length=20), nullable=False),
        sa.Column("is_symmetric", sa.Boolean(), nullable=False),
        sa.Column("pattern_elements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("theme", sa.String(length=100), nullable=True),
        sa.Column("personalization_text", sa.String(length=50), nullable=True),
        sa.Column("additional_instructions", sa.Text(), nullable=True),
        sa.Column("allow_provider_training", sa.Boolean(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("result_storage_path", sa.String(length=2048), nullable=True),
        sa.Column("is_ai_generated", sa.Boolean(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("is_saved", sa.Boolean(), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shared_with_booking_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "body_placement IN ('hand', 'foot', 'arm', 'back', 'other')",
            name=op.f("ck_ai_design_requests_body_placement_valid"),
        ),
        sa.CheckConstraint(
            "density IN ('light', 'medium', 'bold', 'intricate')",
            name=op.f("ck_ai_design_requests_density_valid"),
        ),
        sa.CheckConstraint(
            "difficulty_level IN ('beginner', 'intermediate', 'advanced')",
            name=op.f("ck_ai_design_requests_difficulty_level_valid"),
        ),
        sa.CheckConstraint(
            "occasion IN ('wedding', 'engagement', 'festival', 'baby_shower', 'party', "
            "'corporate_event', 'other')",
            name=op.f("ck_ai_design_requests_occasion_valid"),
        ),
        sa.CheckConstraint(
            "max_retries > 0", name=op.f("ck_ai_design_requests_max_retries_positive")
        ),
        sa.CheckConstraint(
            "retry_count >= 0", name=op.f("ck_ai_design_requests_retry_count_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["generation_id"],
            ["ai_generations.id"],
            name=op.f("fk_ai_design_requests_generation_id_ai_generations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["shared_with_booking_id"],
            ["bookings.id"],
            name=op.f("fk_ai_design_requests_shared_with_booking_id_bookings"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_ai_design_requests_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_design_requests")),
        sa.UniqueConstraint("generation_id", name=op.f("uq_ai_design_requests_generation_id")),
    )
    op.create_index(
        "ix_ai_design_requests_user_id_created_at",
        "ai_design_requests",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_design_requests_user_id_created_at", table_name="ai_design_requests")
    op.drop_table("ai_design_requests")
