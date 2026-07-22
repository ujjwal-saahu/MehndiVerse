"""Admin-curated marketing surfaces — promotional banners, staff-curated
featured design collections, and bulk notification campaigns. All three are
new in Phase 17 (see docs/admin-dashboard.md); none had any schema before
this phase. Distinct from `app/db/models/marketing.py`'s pre-existing
`Coupon`/`CouponRedemption` tables (Phase 2 pre-scaffolding, still unused —
out of scope this phase).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PromoBanner(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A homepage/marketing banner. `starts_at`/`ends_at` are optional
    scheduling bounds — a banner with neither is simply active/inactive per
    `is_active`; the public-facing "is this banner live right now" check
    (not built this phase — no public banner-serving endpoint exists yet)
    would combine both."""

    __tablename__ = "promo_banners"

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(300))
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    link_url: Mapped[str | None] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )


class FeaturedCollection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A staff-curated group of designs for homepage merchandising —
    deliberately a separate table from `collections` (Phase 2's user-owned
    save-collections, `app/db/models/engagement.py`): this one has no
    owning user, is never private, and is edited only by staff."""

    __tablename__ = "featured_collections"

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    cover_image_url: Mapped[str | None] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    items: Mapped[list["FeaturedCollectionItem"]] = relationship(
        back_populates="featured_collection", order_by="FeaturedCollectionItem.sort_order"
    )


class FeaturedCollectionItem(Base):
    __tablename__ = "featured_collection_items"
    __table_args__ = (
        UniqueConstraint(
            "featured_collection_id",
            "design_id",
            name="uq_featured_collection_items_collection_design",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    featured_collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("featured_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    design_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("designs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    featured_collection: Mapped["FeaturedCollection"] = relationship(back_populates="items")


class NotificationCampaign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A staff-authored bulk notification, fanned out to every user matching
    `target_role` (or everyone, if null) at send time via the existing
    per-user `notify_user()` — see docs/admin-dashboard.md#notification-
    campaigns. Sent synchronously (no task-queue infrastructure exists in
    this environment — see docs/booking-messaging.md#3d for the identical
    "foundation, not a scheduler" caveat on reminders); `recipient_count`
    records how many notifications the send actually produced."""

    __tablename__ = "notification_campaigns"
    __table_args__ = (CheckConstraint("status IN ('draft', 'sent')", name="status_valid"),)

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Null means "everyone" — otherwise a stored UserRole value (customer/artist/...).
    target_role: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    recipient_count: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
