"""ai foundation

Phase 20. Extends `ai_generations` (Phase 2 scaffold) into the general
request-record table every AI capability in `app/services/ai/` writes to:
new `entity_type`/`entity_id` polymorphic reference, `model_name` (distinct
from `provider`), retry/attempt tracking, and the confidence/human-review
outcome fields (`confidence`, `requires_human_review`, `review_status`,
`reviewed_by`, `reviewed_at`, `review_notes`). `generation_type`/`status`
gain new enum values (tag_suggestion/embedding_generation/
duplicate_detection/moderation_check; processing).

New tables: `ai_jobs` (the background job queue every capability runs
through — see docs/ai-foundation.md#background-job-processing),
`design_embeddings` (one feature vector per design), `design_tag_
suggestions` (AI-suggested tags awaiting human accept/reject),
`design_duplicate_matches` (near-identical design pairs awaiting staff
review), and `recommendation_events` (append-only interaction log).

Revision ID: b7e2f4a9c1d3
Revises: f1c8a37e5b04
Create Date: 2026-07-22 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2f4a9c1d3"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_GENERATION_TYPES = (
    "design_discovery",
    "photo_preview",
    "generative_design",
    "tag_suggestion",
    "embedding_generation",
    "duplicate_detection",
    "moderation_check",
)
_GENERATION_STATUSES = ("pending", "processing", "completed", "failed")
_REVIEW_STATUSES = ("not_required", "pending", "approved", "rejected")


def upgrade() -> None:
    # --- ai_generations: request-record fields ------------------------------
    op.add_column("ai_generations", sa.Column("entity_type", sa.String(length=30), nullable=True))
    op.add_column(
        "ai_generations", sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column("ai_generations", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("ai_generations", sa.Column("model_name", sa.String(length=100), nullable=True))
    op.add_column(
        "ai_generations",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "ai_generations",
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column("ai_generations", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column(
        "ai_generations",
        sa.Column(
            "requires_human_review", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "ai_generations",
        sa.Column(
            "review_status", sa.String(length=20), nullable=False, server_default="not_required"
        ),
    )
    op.add_column(
        "ai_generations",
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ai_generations", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("ai_generations", sa.Column("review_notes", sa.Text(), nullable=True))
    op.add_column(
        "ai_generations",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        op.f("fk_ai_generations_reviewed_by_users"),
        "ai_generations",
        "users",
        ["reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_ai_generations_entity", "ai_generations", ["entity_type", "entity_id"]
    )

    op.drop_constraint(
        op.f("ck_ai_generations_generation_type_valid"), "ai_generations", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_ai_generations_generation_type_valid"),
        "ai_generations",
        f"generation_type IN ({', '.join(repr(v) for v in _GENERATION_TYPES)})",
    )
    op.drop_constraint(op.f("ck_ai_generations_status_valid"), "ai_generations", type_="check")
    op.create_check_constraint(
        op.f("ck_ai_generations_status_valid"),
        "ai_generations",
        f"status IN ({', '.join(repr(v) for v in _GENERATION_STATUSES)})",
    )
    op.create_check_constraint(
        op.f("ck_ai_generations_review_status_valid"),
        "ai_generations",
        f"review_status IN ({', '.join(repr(v) for v in _REVIEW_STATUSES)})",
    )
    op.create_check_constraint(
        op.f("ck_ai_generations_attempt_count_non_negative"),
        "ai_generations",
        "attempt_count >= 0",
    )
    op.create_check_constraint(
        op.f("ck_ai_generations_max_attempts_positive"), "ai_generations", "max_attempts > 0"
    )
    op.create_check_constraint(
        op.f("ck_ai_generations_confidence_range"),
        "ai_generations",
        "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
    )

    # --- ai_jobs: the background job queue -----------------------------------
    op.create_table(
        "ai_jobs",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("generation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(length=30), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "next_run_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name=op.f("ck_ai_jobs_status_valid"),
        ),
        sa.CheckConstraint("attempt_count >= 0", name=op.f("ck_ai_jobs_attempt_count_non_negative")),
        sa.CheckConstraint("max_attempts > 0", name=op.f("ck_ai_jobs_max_attempts_positive")),
        sa.ForeignKeyConstraint(
            ["generation_id"], ["ai_generations.id"],
            name=op.f("fk_ai_jobs_generation_id_ai_generations"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_jobs")),
    )
    op.create_index("ix_ai_jobs_generation_id", "ai_jobs", ["generation_id"])
    op.create_index("ix_ai_jobs_status_next_run_at", "ai_jobs", ["status", "next_run_at"])

    # --- design_embeddings -----------------------------------------------------
    op.create_table(
        "design_embeddings",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("dimension > 0", name=op.f("ck_design_embeddings_dimension_positive")),
        sa.ForeignKeyConstraint(
            ["design_id"], ["designs.id"],
            name=op.f("fk_design_embeddings_design_id_designs"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_design_embeddings")),
        sa.UniqueConstraint("design_id", name="uq_design_embeddings_design_id"),
    )

    # --- design_tag_suggestions -------------------------------------------------
    op.create_table(
        "design_tag_suggestions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_name", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name=op.f("ck_design_tag_suggestions_status_valid"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_design_tag_suggestions_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["design_id"], ["designs.id"],
            name=op.f("fk_design_tag_suggestions_design_id_designs"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"], ["users.id"],
            name=op.f("fk_design_tag_suggestions_resolved_by_users"), ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_design_tag_suggestions")),
        sa.UniqueConstraint(
            "design_id", "tag_name", name="uq_design_tag_suggestions_design_tag"
        ),
    )
    op.create_index(
        "ix_design_tag_suggestions_design_id", "design_tag_suggestions", ["design_id"]
    )

    # --- design_duplicate_matches ------------------------------------------------
    op.create_table(
        "design_duplicate_matches",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("matched_design_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("similarity", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'dismissed')",
            name=op.f("ck_design_duplicate_matches_status_valid"),
        ),
        sa.CheckConstraint(
            "similarity >= 0 AND similarity <= 1",
            name=op.f("ck_design_duplicate_matches_similarity_range"),
        ),
        sa.CheckConstraint(
            "design_id <> matched_design_id",
            name=op.f("ck_design_duplicate_matches_design_id_not_self"),
        ),
        sa.ForeignKeyConstraint(
            ["design_id"], ["designs.id"],
            name=op.f("fk_design_duplicate_matches_design_id_designs"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["matched_design_id"], ["designs.id"],
            name=op.f("fk_design_duplicate_matches_matched_design_id_designs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"], ["users.id"],
            name=op.f("fk_design_duplicate_matches_resolved_by_users"), ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_design_duplicate_matches")),
        sa.UniqueConstraint(
            "design_id", "matched_design_id", name="uq_design_duplicate_matches_pair"
        ),
    )
    op.create_index(
        "ix_design_duplicate_matches_design_id", "design_duplicate_matches", ["design_id"]
    )

    # --- recommendation_events ------------------------------------------------
    op.create_table(
        "recommendation_events",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('view', 'like', 'save', 'search_click', 'booking_request')",
            name=op.f("ck_recommendation_events_event_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name=op.f("fk_recommendation_events_user_id_users"), ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["design_id"], ["designs.id"],
            name=op.f("fk_recommendation_events_design_id_designs"), ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_events")),
    )
    op.create_index("ix_recommendation_events_user_id", "recommendation_events", ["user_id"])
    op.create_index("ix_recommendation_events_design_id", "recommendation_events", ["design_id"])


def downgrade() -> None:
    op.drop_index("ix_recommendation_events_design_id", table_name="recommendation_events")
    op.drop_index("ix_recommendation_events_user_id", table_name="recommendation_events")
    op.drop_table("recommendation_events")

    op.drop_index(
        "ix_design_duplicate_matches_design_id", table_name="design_duplicate_matches"
    )
    op.drop_table("design_duplicate_matches")

    op.drop_index("ix_design_tag_suggestions_design_id", table_name="design_tag_suggestions")
    op.drop_table("design_tag_suggestions")

    op.drop_table("design_embeddings")

    op.drop_index("ix_ai_jobs_status_next_run_at", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_generation_id", table_name="ai_jobs")
    op.drop_table("ai_jobs")

    op.drop_constraint(op.f("ck_ai_generations_confidence_range"), "ai_generations", type_="check")
    op.drop_constraint(
        op.f("ck_ai_generations_max_attempts_positive"), "ai_generations", type_="check"
    )
    op.drop_constraint(
        op.f("ck_ai_generations_attempt_count_non_negative"), "ai_generations", type_="check"
    )
    op.drop_constraint(op.f("ck_ai_generations_review_status_valid"), "ai_generations", type_="check")
    op.drop_constraint(op.f("ck_ai_generations_status_valid"), "ai_generations", type_="check")
    op.create_check_constraint(
        op.f("ck_ai_generations_status_valid"),
        "ai_generations",
        "status IN ('pending', 'completed', 'failed')",
    )
    op.drop_constraint(
        op.f("ck_ai_generations_generation_type_valid"), "ai_generations", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_ai_generations_generation_type_valid"),
        "ai_generations",
        "generation_type IN ('design_discovery', 'photo_preview', 'generative_design')",
    )

    op.drop_index("ix_ai_generations_entity", table_name="ai_generations")
    op.drop_constraint(
        op.f("fk_ai_generations_reviewed_by_users"), "ai_generations", type_="foreignkey"
    )
    op.drop_column("ai_generations", "updated_at")
    op.drop_column("ai_generations", "review_notes")
    op.drop_column("ai_generations", "reviewed_at")
    op.drop_column("ai_generations", "reviewed_by")
    op.drop_column("ai_generations", "review_status")
    op.drop_column("ai_generations", "requires_human_review")
    op.drop_column("ai_generations", "confidence")
    op.drop_column("ai_generations", "max_attempts")
    op.drop_column("ai_generations", "attempt_count")
    op.drop_column("ai_generations", "model_name")
    op.drop_column("ai_generations", "error_message")
    op.drop_column("ai_generations", "entity_id")
    op.drop_column("ai_generations", "entity_type")
