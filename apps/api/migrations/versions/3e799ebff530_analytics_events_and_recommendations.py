"""analytics events and recommendations

Phase 22. Replaces Phase 20's `recommendation_events` table (collection-only,
never actually read by anything — see `AnalyticsEventType`'s docstring) with
`analytics_events`: a general product-analytics event log covering the full
Phase 22 event list (app opened, registration completed, design viewed/
liked/saved, artist viewed, booking started/submitted, quote accepted,
payment completed, subscription started, AI generation requested, preview
created, design shared). `search_performed`/`filter_applied` are tracked via
the pre-existing `search_events` table instead — see docs/analytics-and-
recommendations.md#search-analytics.

Also adds `user_preferences.analytics_consent` (default `False`, mirroring
`marketing_opt_in`'s existing opt-in-required precedent) — see
docs/analytics-and-recommendations.md#provide-analytics-consent-where-
legally-required.

Revision ID: 3e799ebff530
Revises: 4d731f224f04
Create Date: 2026-07-21 12:52:11.777137

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3e799ebff530"
down_revision: str | Sequence[str] | None = "4d731f224f04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EVENT_TYPES = (
    "app_opened",
    "registration_completed",
    "design_viewed",
    "design_liked",
    "design_saved",
    "artist_viewed",
    "booking_started",
    "booking_submitted",
    "quote_accepted",
    "payment_completed",
    "subscription_started",
    "ai_generation_requested",
    "preview_created",
    "design_shared",
)


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=True),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "event_type IN (" + ", ".join(f"'{value}'" for value in _EVENT_TYPES) + ")",
            name=op.f("ck_analytics_events_event_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_analytics_events_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analytics_events")),
    )
    op.create_index("ix_analytics_events_entity", "analytics_events", ["entity_type", "entity_id"])
    op.create_index(
        "ix_analytics_events_event_type_created_at",
        "analytics_events",
        ["event_type", "created_at"],
    )
    op.create_index(
        "ix_analytics_events_user_id_created_at", "analytics_events", ["user_id", "created_at"]
    )

    op.drop_index("ix_recommendation_events_design_id", table_name="recommendation_events")
    op.drop_index("ix_recommendation_events_user_id", table_name="recommendation_events")
    op.drop_table("recommendation_events")

    op.add_column(
        "user_preferences",
        sa.Column("analytics_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("user_preferences", "analytics_consent", server_default=None)


def downgrade() -> None:
    op.drop_column("user_preferences", "analytics_consent")

    op.create_table(
        "recommendation_events",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), autoincrement=False, nullable=True),
        sa.Column("session_id", sa.VARCHAR(length=100), autoincrement=False, nullable=True),
        sa.Column("design_id", sa.UUID(), autoincrement=False, nullable=True),
        sa.Column("event_type", sa.VARCHAR(length=30), autoincrement=False, nullable=False),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('view', 'like', 'save', 'search_click', 'booking_request')",
            name=op.f("ck_recommendation_events_event_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["design_id"],
            ["designs.id"],
            name=op.f("fk_recommendation_events_design_id_designs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_recommendation_events_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_events")),
    )
    op.create_index("ix_recommendation_events_user_id", "recommendation_events", ["user_id"])
    op.create_index("ix_recommendation_events_design_id", "recommendation_events", ["design_id"])

    op.drop_index("ix_analytics_events_user_id_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_event_type_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_entity", table_name="analytics_events")
    op.drop_table("analytics_events")
