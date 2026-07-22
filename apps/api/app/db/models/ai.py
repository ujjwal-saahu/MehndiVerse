import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import (
    AiGenerationStatus,
    AiGenerationType,
    AiJobStatus,
    AiReviewStatus,
    BodyPlacement,
    BookingEventType,
    DesignDifficulty,
    DuplicateMatchStatus,
    PatternDensity,
    PreviewProjectStatus,
    TagSuggestionStatus,
    check_in,
)
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class PreviewProject(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Hand/foot photo preview projects — user-deletable, hence soft delete.
    See docs/hand-foot-preview.md.

    `source_storage_path`/`result_storage_path` are bucket-relative paths in
    the private `preview-projects` bucket, deliberately not URLs — same
    "no durable public URL, mint a signed one on demand" treatment as
    `ArtistDocument.storage_path` (see
    docs/artist-verification.md#document-privacy). These are real photos of
    a customer's hand/foot, not marketing content, so they get the private-
    bucket treatment `portfolio`/`avatars` don't need.

    `overlay_transform` holds the design-overlay's position/scale/rotation/
    flip/opacity, all editor state a client needs to resume editing exactly
    where it left off — see docs/hand-foot-preview.md#editable-preview-state.
    Compositing (drawing the overlay onto the photo) happens client-side;
    the backend never rasterizes anything itself.
    """

    __tablename__ = "preview_projects"
    __table_args__ = (
        CheckConstraint(check_in("status", PreviewProjectStatus), name="status_valid"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    design_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("designs.id", ondelete="SET NULL")
    )
    source_storage_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    result_storage_path: Mapped[str | None] = mapped_column(String(2048))
    source_width: Mapped[int | None] = mapped_column(Integer)
    source_height: Mapped[int | None] = mapped_column(Integer)
    # {x, y (0..1 fractions of photo size), scale, rotation_degrees,
    # flip_horizontal, opacity} — see app/schemas/preview.py::OverlayTransform.
    overlay_transform: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PreviewProjectStatus.PENDING.value
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    # Set by "send to artist" — grants the artist on this booking read
    # access to this one preview, without making it public. See
    # docs/hand-foot-preview.md#send-to-artist.
    shared_with_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL")
    )


class AiGeneration(UUIDPrimaryKeyMixin, Base):
    """Append-only log of every AI call this module makes — discovery
    queries, preview jobs, tag suggestions, embeddings, duplicate checks,
    moderation checks — for audit/cost tracking. See docs/ai-foundation.md
    #ai-request-records. No soft delete (financial/audit-trail-adjacent);
    `updated_at` exists (unlike the original append-only design) because a
    job-backed record's `status` legitimately transitions after creation
    (pending -> processing -> completed|failed).

    `entity_type`/`entity_id` is a polymorphic reference to whatever this
    call is *about* (a `Design` for tagging/embeddings/moderation/
    duplicates; null for a freeform discovery-style query) — mirrors
    `Report.reported_entity_type`/`reported_entity_id`'s precedent
    (app/db/models/moderation.py).
    """

    __tablename__ = "ai_generations"
    __table_args__ = (
        CheckConstraint(
            check_in("generation_type", AiGenerationType), name="generation_type_valid"
        ),
        CheckConstraint(check_in("status", AiGenerationStatus), name="status_valid"),
        CheckConstraint(check_in("review_status", AiReviewStatus), name="review_status_valid"),
        CheckConstraint("cost_usd IS NULL OR cost_usd >= 0", name="cost_usd_non_negative"),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="latency_ms_non_negative"),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        CheckConstraint("max_attempts > 0", name="max_attempts_positive"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),
        Index("ix_ai_generations_entity", "entity_type", "entity_id"),
    )

    # Nullable: guest usage is tracked via guest_session_id instead of a user FK.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    guest_session_id: Mapped[str | None] = mapped_column(String(100))
    generation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(30))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AiGenerationStatus.PENDING.value
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    # Provider/model metadata — never a raw API key or credential (see
    # docs/ai-foundation.md#never-expose-provider-keys).
    provider: Mapped[str | None] = mapped_column(String(50))
    model_name: Mapped[str | None] = mapped_column(String(100))
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 4))
    latency_ms: Mapped[int | None] = mapped_column()
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    # The outcome's own confidence (0..1) — distinct from job success.
    confidence: Mapped[float | None] = mapped_column(Float)
    requires_human_review: Mapped[bool] = mapped_column(default=False, nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AiReviewStatus.NOT_REQUIRED.value
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AiJob(UUIDPrimaryKeyMixin, Base):
    """The background job queue every AI capability in this module runs
    through — see docs/ai-foundation.md#background-job-processing. A plain
    database-table queue (claimed via an atomic conditional UPDATE, see
    app/services/ai/jobs.py::claim_due_jobs), not Celery/RQ — same "no real
    background worker provisioned yet" foundation precedent as every other
    phase's queued-work story (e.g. app/services/design_image_processing.py),
    except this is the first phase to actually give that queue a durable,
    inspectable table instead of running inline. `python -m
    app.cli.process_ai_jobs` is the worker; swapping it for a real queue
    later only means changing `enqueue_job`/the worker script, never any
    caller.
    """

    __tablename__ = "ai_jobs"
    __table_args__ = (
        CheckConstraint(check_in("status", AiJobStatus), name="status_valid"),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        CheckConstraint("max_attempts > 0", name="max_attempts_positive"),
        Index("ix_ai_jobs_status_next_run_at", "status", "next_run_at"),
    )

    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(30), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AiJobStatus.PENDING.value
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    # When this job becomes eligible to run — set to now() on enqueue, and
    # pushed into the future (exponential backoff) on a retryable failure.
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DesignEmbedding(UUIDPrimaryKeyMixin, Base):
    """One feature vector per design, recomputed (upserted, never
    duplicated — `design_id` is unique) whenever a design's primary image
    changes. Powers similar-design search and duplicate-image detection —
    see docs/ai-foundation.md#image-embedding-generation. Stored as a plain
    JSONB float array rather than a `vector` column: no pgvector extension
    is provisioned in this environment (see docs/ai-foundation.md#similarity-
    search-is-a-foundation for the scaling note)."""

    __tablename__ = "design_embeddings"
    __table_args__ = (
        UniqueConstraint("design_id", name="uq_design_embeddings_design_id"),
        CheckConstraint("dimension > 0", name="dimension_positive"),
    )

    design_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"), nullable=False
    )
    embedding: Mapped[list[float]] = mapped_column(JSONB, nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DesignTagSuggestion(UUIDPrimaryKeyMixin, Base):
    """AI-suggested tags for a design, awaiting the owning artist's or
    staff's accept/reject decision — never auto-applied to
    `design_tags` (see docs/ai-foundation.md#automatic-design-tag-
    suggestion). `UniqueConstraint(design_id, tag_name)` makes re-running
    tag suggestion for the same design retry-safe: a re-run upserts the
    confidence on an existing pending suggestion rather than duplicating
    it, and never overwrites one a human has already decided on."""

    __tablename__ = "design_tag_suggestions"
    __table_args__ = (
        UniqueConstraint("design_id", "tag_name", name="uq_design_tag_suggestions_design_tag"),
        CheckConstraint(check_in("status", TagSuggestionStatus), name="status_valid"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
    )

    design_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag_name: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TagSuggestionStatus.PENDING.value
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DesignDuplicateMatch(UUIDPrimaryKeyMixin, Base):
    """A pair of designs whose embeddings are near-identical — see
    docs/ai-foundation.md#duplicate-image-detection. Feeds the same
    human-review discipline as moderation: a match is `pending` until
    staff confirms or dismisses it; nothing is auto-removed."""

    __tablename__ = "design_duplicate_matches"
    __table_args__ = (
        UniqueConstraint("design_id", "matched_design_id", name="uq_design_duplicate_matches_pair"),
        CheckConstraint(check_in("status", DuplicateMatchStatus), name="status_valid"),
        CheckConstraint("similarity >= 0 AND similarity <= 1", name="similarity_range"),
        CheckConstraint("design_id <> matched_design_id", name="design_id_not_self"),
    )

    design_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matched_design_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"), nullable=False
    )
    similarity: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DuplicateMatchStatus.PENDING.value
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AiDesignRequest(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Personalized AI design generation — see docs/ai-design-assistant.md.

    One row per structured-form submission. `generation_id` is a one-to-one
    link to the `AiGeneration` row that actually tracks job status, provider/
    model metadata, cost, latency, and human-review state (see
    docs/ai-foundation.md#ai-request-records) — this table only holds the
    Phase 21-specific structured-form fields and the generation result,
    rather than duplicating status/cost bookkeeping Phase 20 already built.

    `is_ai_generated` is always `True` — stored explicitly (not just implied
    by the table's existence) so a schema/serializer bug can never silently
    drop the "this is AI-generated, not a human artist's work" label a
    client renders. See docs/ai-design-assistant.md#ai-generated-label.

    `allow_provider_training` defaults to `False` and is never assumed
    `True` — see docs/ai-design-assistant.md#consent-for-provider-training.

    Soft-deletable (a user can remove an unwanted entry from their
    generation history); no financial/audit-trail reason to keep it forever
    the way `AiGeneration` itself is kept.
    """

    __tablename__ = "ai_design_requests"
    __table_args__ = (
        CheckConstraint(check_in("body_placement", BodyPlacement), name="body_placement_valid"),
        CheckConstraint(
            check_in("difficulty_level", DesignDifficulty), name="difficulty_level_valid"
        ),
        CheckConstraint(check_in("occasion", BookingEventType), name="occasion_valid"),
        CheckConstraint(check_in("density", PatternDensity), name="density_valid"),
        CheckConstraint("retry_count >= 0", name="retry_count_non_negative"),
        CheckConstraint("max_retries > 0", name="max_retries_positive"),
        Index("ix_ai_design_requests_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    generation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_generations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # --- structured form (docs/ai-design-assistant.md#structured-form) ---
    style: Mapped[str] = mapped_column(String(100), nullable=False)
    occasion: Mapped[str] = mapped_column(String(30), nullable=False)
    body_placement: Mapped[str] = mapped_column(String(20), nullable=False)
    difficulty_level: Mapped[str] = mapped_column(String(20), nullable=False)
    density: Mapped[str] = mapped_column(String(20), nullable=False)
    is_symmetric: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pattern_elements: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    theme: Mapped[str | None] = mapped_column(String(100))
    personalization_text: Mapped[str | None] = mapped_column(String(50))
    additional_instructions: Mapped[str | None] = mapped_column(Text)
    allow_provider_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # --- prompt / result ---
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    result_storage_path: Mapped[str | None] = mapped_column(String(2048))
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # --- retry (docs/ai-design-assistant.md#generation-failure-and-retry) ---
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # --- save / share ---
    is_saved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shared_with_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL")
    )
