import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import (
    BodyPlacement,
    CategoryType,
    DesignDifficulty,
    DesignImageStatus,
    DesignStatus,
    check_in,
)
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.artist import ArtistProfile


class Design(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "designs"
    __table_args__ = (
        CheckConstraint(
            check_in("difficulty_level", DesignDifficulty), name="difficulty_level_valid"
        ),
        CheckConstraint(check_in("body_placement", BodyPlacement), name="body_placement_valid"),
        CheckConstraint(check_in("status", DesignStatus), name="status_valid"),
        CheckConstraint("view_count >= 0", name="view_count_non_negative"),
        CheckConstraint("like_count >= 0", name="like_count_non_negative"),
        # Composite, keyset-pagination-friendly indexes for the three home-feed
        # sections (see docs/design-gallery.md#query-optimization) — each
        # leads with `status` so a plain `status = 'published'` filter can
        # also use these via the leftmost-column prefix, making the old
        # single-column ix_designs_status redundant.
        Index("ix_designs_status_created_at_id", "status", "created_at", "id"),
        Index("ix_designs_status_is_featured_created_at", "status", "is_featured", "created_at"),
        Index("ix_designs_status_view_count_id", "status", "view_count", "id"),
        # "Most saved" sort — see docs/design-search.md#most-saved-is-a-foundation.
        Index("ix_designs_status_save_count_id", "status", "save_count", "id"),
        # GIN index over the generated tsvector, for `@@` full-text queries —
        # see docs/design-search.md#postgresql-full-text-search.
        Index("ix_designs_search_vector", "search_vector", postgresql_using="gin"),
        # Functional btree index supporting fast `lower(title) LIKE 'prefix%'`
        # suggestion lookups (see docs/design-search.md#search-suggestions)
        # without needing the pg_trgm extension.
        Index("ix_designs_title_lower_pattern", text("lower(title) text_pattern_ops")),
        CheckConstraint("save_count >= 0", name="save_count_non_negative"),
    )

    # NULL artist_profile_id means a platform/admin-curated design, not tied to
    # a specific artist's portfolio.
    artist_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artist_profiles.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    difficulty_level: Mapped[str | None] = mapped_column(String(20))
    body_placement: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DesignStatus.DRAFT.value
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Foundation for the "most saved" sort (see docs/design-search.md) — no
    # "save to collection" endpoint exists yet (Phase 2's `collections` /
    # `collection_items` tables aren't wired to an API), so this stays 0
    # until that feature increments it. Mirrors `view_count`/`like_count`'s
    # denormalized-counter pattern rather than a live COUNT() at query time.
    save_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Generated (STORED) column, not maintained by the application — Postgres
    # recomputes it automatically whenever title/description change, so it
    # can never drift out of sync. Deliberately title+description only, not
    # tags/categories (a generated column can't reference other tables) —
    # see docs/design-search.md#postgresql-full-text-search.
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))",
            persisted=True,
        ),
    )

    artist_profile: Mapped["ArtistProfile | None"] = relationship()
    images: Mapped[list["DesignImage"]] = relationship(back_populates="design")


class DesignImage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """`image_url` is nullable because a row exists (in `pending` status) from
    the moment upload is *authorized*, before any bytes have arrived — see
    docs/design-catalog.md#image-upload-pipeline. Only `ready` images should
    ever be shown to anyone but the owner/staff (enforced at the route layer,
    not the database)."""

    __tablename__ = "design_images"
    __table_args__ = (
        UniqueConstraint("design_id", "sort_order", name="uq_design_images_sort_order"),
        CheckConstraint(check_in("status", DesignImageStatus), name="status_valid"),
        CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0", name="file_size_bytes_non_negative"
        ),
    )

    design_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DesignImageStatus.PENDING.value
    )
    image_url: Mapped[str | None] = mapped_column(String(2048))
    thumbnail_small_url: Mapped[str | None] = mapped_column(String(2048))
    thumbnail_medium_url: Mapped[str | None] = mapped_column(String(2048))
    storage_path: Mapped[str | None] = mapped_column(String(2048))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    processing_error: Mapped[str | None] = mapped_column(String(500))

    design: Mapped["Design"] = relationship(back_populates="images")


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """`category_type` groups rows into one of six taxonomy axes (style,
    occasion, body_part, difficulty, density, region) — see
    docs/design-catalog.md#category-taxonomy. A design can belong to any
    number of categories across any number of axes via `design_categories`."""

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("name", name="uq_categories_name"),
        UniqueConstraint("slug", name="uq_categories_slug"),
        CheckConstraint(check_in("category_type", CategoryType), name="category_type_valid"),
        Index("ix_categories_category_type", "category_type"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    category_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    parent_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL")
    )
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DesignCategory(Base):
    """Join table: designs <-> categories (many-to-many). The composite
    primary key (design_id, category_id) already indexes `design_id` as its
    leading column; category browsing filters the other direction (`WHERE
    category_id = ...`), which needs its own index to avoid a full scan."""

    __tablename__ = "design_categories"
    __table_args__ = (Index("ix_design_categories_category_id", "category_id"),)

    design_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Tag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("name", name="uq_tags_name"),
        UniqueConstraint("slug", name="uq_tags_slug"),
    )

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False)


class DesignTag(Base):
    """Join table: designs <-> tags (many-to-many)."""

    __tablename__ = "design_tags"

    design_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
