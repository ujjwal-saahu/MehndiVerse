import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import (
    ArtistVerificationStatus,
    BlockedDateType,
    DocumentStatus,
    DocumentType,
    PricingType,
    check_in,
)
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.user import User


class ArtistProfile(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "artist_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_artist_profiles_user_id"),
        CheckConstraint(
            check_in("verification_status", ArtistVerificationStatus),
            name="verification_status_valid",
        ),
        CheckConstraint("rating_average >= 0 AND rating_average <= 5", name="rating_average_range"),
        CheckConstraint("rating_count >= 0", name="rating_count_non_negative"),
        CheckConstraint("follower_count >= 0", name="follower_count_non_negative"),
        CheckConstraint("default_buffer_minutes >= 0", name="default_buffer_minutes_non_negative"),
        CheckConstraint(
            "default_travel_buffer_minutes >= 0",
            name="default_travel_buffer_minutes_non_negative",
        ),
        Index(
            "ix_artist_profiles_verification_status_rating_average",
            "verification_status",
            "rating_average",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    business_name: Mapped[str | None] = mapped_column(String(150))
    # The public display name on the artist's profile — distinct from
    # `business_name` (a studio/brand name an artist may or may not have).
    professional_name: Mapped[str | None] = mapped_column(String(150))
    headline: Mapped[str | None] = mapped_column(String(200))
    bio: Mapped[str | None] = mapped_column(Text)
    years_experience: Mapped[int | None] = mapped_column(SmallInteger)
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ArtistVerificationStatus.DRAFT.value
    )
    # Set/cleared across the onboarding lifecycle — see
    # docs/artist-verification.md#verification-lifecycle. `reviewed_by`/
    # `reviewed_at` reflect the *last* staff action of any kind (approve,
    # reject, request-info, suspend, reinstate); the full history of every
    # action lives in `audit_logs`, not here.
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    more_info_request: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(2))
    # Cities/regions the artist travels to for on-location bookings, beyond
    # their home `city` — a simple string list, not a normalized table:
    # there's no need to query "all artists servicing area X" yet.
    service_areas: Mapped[list[str] | None] = mapped_column(JSONB)
    languages: Mapped[list[str] | None] = mapped_column(JSONB)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(30))
    # {"instagram": "https://...", "website": "https://...", ...} — free-form
    # platform -> URL, validated (known platform keys, well-formed URLs) at
    # the API layer, not the DB.
    social_links: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    profile_image_url: Mapped[str | None] = mapped_column(String(2048))
    cover_image_url: Mapped[str | None] = mapped_column(String(2048))
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    rating_average: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0)
    rating_count: Mapped[int] = mapped_column(nullable=False, default=0)
    # Denormalized counter, atomically maintained by
    # app/services/artist_directory.py::follow_artist/unfollow_artist —
    # mirrors designs.like_count/save_count's pattern rather than a live
    # COUNT() at read time. See docs/artist-directory.md#follow-foundation.
    follower_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_accepting_bookings: Mapped[bool] = mapped_column(default=True, nullable=False)
    # IANA zone name (e.g. "Asia/Kolkata"), never a fixed UTC offset — see
    # docs/artist-scheduling.md#timezone-strategy. Recurring weekly
    # availability is stored as local wall-clock time interpreted against
    # this zone, so DST transitions never shift what "9am" means.
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    # Artist-level defaults; `ArtistService.buffer_minutes`/
    # `travel_buffer_minutes` override these per service when set. See
    # docs/artist-scheduling.md#buffer-time-and-travel-buffer.
    default_buffer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    default_travel_buffer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    # passive_deletes=True: these children use ON DELETE CASCADE at the DB
    # level — let Postgres cascade the delete directly (see user.py for the
    # same pattern).
    documents: Mapped[list["ArtistDocument"]] = relationship(
        back_populates="artist_profile", passive_deletes=True
    )
    services: Mapped[list["ArtistService"]] = relationship(
        back_populates="artist_profile", passive_deletes=True
    )
    availability_slots: Mapped[list["ArtistAvailability"]] = relationship(
        back_populates="artist_profile", passive_deletes=True
    )
    blocked_dates: Mapped[list["ArtistBlockedDate"]] = relationship(
        back_populates="artist_profile", passive_deletes=True
    )


class ArtistDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Verification documents. No soft delete: rejected/withdrawn documents stay
    as an audit trail of the verification process."""

    __tablename__ = "artist_documents"
    __table_args__ = (
        CheckConstraint(check_in("document_type", DocumentType), name="document_type_valid"),
        CheckConstraint(check_in("status", DocumentStatus), name="status_valid"),
        CheckConstraint("file_size_bytes > 0", name="file_size_bytes_positive"),
    )

    artist_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artist_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Bucket-relative path in the private `verification-documents` bucket —
    # deliberately not a URL: the bucket is private, so nothing durable
    # should be resolvable without a signed URL minted on demand at read
    # time. See docs/artist-verification.md#document-privacy.
    storage_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DocumentStatus.PENDING.value
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(String(500))

    artist_profile: Mapped["ArtistProfile"] = relationship(back_populates="documents")


class ArtistService(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "artist_services"
    __table_args__ = (
        CheckConstraint(check_in("pricing_type", PricingType), name="pricing_type_valid"),
        CheckConstraint(
            "price_amount IS NULL OR price_amount >= 0", name="price_amount_non_negative"
        ),
        CheckConstraint("price_min IS NULL OR price_min >= 0", name="price_min_non_negative"),
        CheckConstraint(
            "price_max IS NULL OR price_min IS NULL OR price_max >= price_min",
            name="price_max_gte_price_min",
        ),
        CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes > 0", name="duration_positive"
        ),
        CheckConstraint(
            "customer_capacity IS NULL OR customer_capacity > 0",
            name="customer_capacity_positive",
        ),
        CheckConstraint(
            "deposit_amount IS NULL OR deposit_amount >= 0", name="deposit_amount_non_negative"
        ),
        CheckConstraint(
            "travel_charge_amount IS NULL OR travel_charge_amount >= 0",
            name="travel_charge_amount_non_negative",
        ),
        CheckConstraint(
            "buffer_minutes IS NULL OR buffer_minutes >= 0", name="buffer_minutes_non_negative"
        ),
        CheckConstraint(
            "travel_buffer_minutes IS NULL OR travel_buffer_minutes >= 0",
            name="travel_buffer_minutes_non_negative",
        ),
    )

    artist_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artist_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    pricing_type: Mapped[str] = mapped_column(String(20), nullable=False)
    price_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    price_min: Mapped[float | None] = mapped_column(Numeric(10, 2))
    price_max: Mapped[float | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column()
    customer_capacity: Mapped[int | None] = mapped_column(Integer)
    deposit_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    deposit_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    travel_charge_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    cancellation_policy: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    # Overrides ArtistProfile.default_buffer_minutes/
    # default_travel_buffer_minutes when set. See
    # docs/artist-scheduling.md#buffer-time-and-travel-buffer.
    buffer_minutes: Mapped[int | None] = mapped_column(Integer)
    travel_buffer_minutes: Mapped[int | None] = mapped_column(Integer)

    artist_profile: Mapped["ArtistProfile"] = relationship(back_populates="services")


class ArtistAvailability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Recurring weekly availability slots."""

    __tablename__ = "artist_availability"
    __table_args__ = (
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="day_of_week_range"),
        CheckConstraint("end_time > start_time", name="end_time_after_start_time"),
        UniqueConstraint(
            "artist_profile_id",
            "day_of_week",
            "start_time",
            "end_time",
            name="uq_artist_availability_slot",
        ),
    )

    artist_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artist_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    artist_profile: Mapped["ArtistProfile"] = relationship(back_populates="availability_slots")


class ArtistBlockedDate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Blackout dates — holidays, vacation, personal leave, and one-off
    "manual schedule block"s all share this table, distinguished by
    `block_type`. When `start_time`/`end_time` are both null, the whole day
    (or date range) is blocked; when set, only that time-of-day window on a
    single day is blocked (`start_date == end_date` is enforced). See
    docs/artist-scheduling.md#blocked-dates-holidays-and-personal-leave."""

    __tablename__ = "artist_blocked_dates"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="end_date_gte_start_date"),
        CheckConstraint(check_in("block_type", BlockedDateType), name="block_type_valid"),
        CheckConstraint(
            "(start_time IS NULL AND end_time IS NULL) OR "
            "(start_time IS NOT NULL AND end_time IS NOT NULL AND end_time > start_time "
            "AND start_date = end_date)",
            name="time_range_consistent",
        ),
    )

    artist_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artist_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    block_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BlockedDateType.OTHER.value
    )
    # Both null => the whole date range is blocked. Both set => only this
    # time-of-day window on `start_date` (== `end_date`) is blocked — the
    # "manual schedule block" case.
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    reason: Mapped[str | None] = mapped_column(String(255))

    artist_profile: Mapped["ArtistProfile"] = relationship(back_populates="blocked_dates")
