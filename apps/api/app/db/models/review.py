import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Review(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Soft-deleted (not hard-deleted) so rating aggregates can be recomputed
    consistently and moderation actions leave a trace."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_reviews_booking_id"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    artist_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artist_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    artist_response: Mapped[str | None] = mapped_column(Text)
    artist_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
