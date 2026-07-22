import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.enums import (
    AttachmentFileType,
    BookingEventType,
    BookingLocationType,
    BookingStatus,
    QuoteStatus,
    check_in,
)
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Bookings and their history are never soft-deleted or hard-deleted: they are
# the audit trail of the marketplace transaction. Cancellation is represented
# as a status (CANCELLED), never a row deletion. See docs/booking-lifecycle.md.


class Booking(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(check_in("status", BookingStatus), name="status_valid"),
        CheckConstraint(check_in("location_type", BookingLocationType), name="location_type_valid"),
        CheckConstraint(
            "deposit_amount IS NULL OR deposit_amount >= 0", name="deposit_amount_non_negative"
        ),
        CheckConstraint(
            "total_amount IS NULL OR total_amount >= 0", name="total_amount_non_negative"
        ),
        CheckConstraint(
            "event_type IS NULL OR " + check_in("event_type", BookingEventType),
            name="event_type_valid",
        ),
        CheckConstraint(
            "num_customers IS NULL OR num_customers > 0", name="num_customers_positive"
        ),
        CheckConstraint("budget_min IS NULL OR budget_min >= 0", name="budget_min_non_negative"),
        CheckConstraint(
            "budget_max IS NULL OR budget_min IS NULL OR budget_max >= budget_min",
            name="budget_max_gte_budget_min",
        ),
        Index(
            "ix_bookings_artist_profile_id_status_requested_date",
            "artist_profile_id",
            "status",
            "requested_date",
        ),
        # Backs GET /bookings/mine's customer_id filter + created_at DESC
        # sort — see migrations/versions/8f509ffde693.
        Index("ix_bookings_customer_id_created_at", "customer_id", "created_at"),
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
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artist_services.id", ondelete="SET NULL")
    )
    design_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("designs.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BookingStatus.DRAFT.value, index=True
    )
    # Nullable: a draft may not have decided these yet. Required at
    # submission — see app/services/booking.py::missing_submission_requirements.
    requested_date: Mapped[date | None] = mapped_column(Date)
    requested_time: Mapped[time | None] = mapped_column(Time)
    location_type: Mapped[str | None] = mapped_column(String(30))
    location_address: Mapped[str | None] = mapped_column(Text)
    # "Event type" — see BookingEventType. "Number of customers" getting
    # mehndi done. "Design preferences" is free text describing the desired
    # style; a specific reference design is `design_id` above. `notes` is the
    # general-purpose "customer notes" field.
    event_type: Mapped[str | None] = mapped_column(String(30))
    num_customers: Mapped[int | None] = mapped_column(Integer)
    design_preferences: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    budget_min: Mapped[float | None] = mapped_column(Numeric(10, 2))
    budget_max: Mapped[float | None] = mapped_column(Numeric(10, 2))
    # Booking-specific contact details — may differ from the customer's
    # account email/phone (e.g. a family member coordinating the booking).
    contact_name: Mapped[str | None] = mapped_column(String(150))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(30))
    deposit_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    total_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(500))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # passive_deletes=True: these children use ON DELETE RESTRICT at the DB
    # level, so the ORM should not try to load and null out their FK on
    # parent delete — let Postgres enforce (and raise on) the restriction.
    quotes: Mapped[list["BookingQuote"]] = relationship(
        back_populates="booking", passive_deletes=True
    )
    status_history: Mapped[list["BookingStatusHistory"]] = relationship(
        back_populates="booking", passive_deletes=True
    )
    attachments: Mapped[list["BookingAttachment"]] = relationship(
        back_populates="booking", passive_deletes=True
    )


class BookingQuote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A booking may accumulate multiple quotes over time (renegotiation); only
    one should be PENDING or ACCEPTED at a time — enforced at the service layer
    in a later phase, not by a DB constraint (see docs/booking-lifecycle.md)."""

    __tablename__ = "booking_quotes"
    __table_args__ = (
        CheckConstraint(check_in("status", QuoteStatus), name="status_valid"),
        CheckConstraint("amount > 0", name="amount_positive"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    terms: Mapped[str | None] = mapped_column(Text)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=QuoteStatus.PENDING.value
    )

    booking: Mapped["Booking"] = relationship(back_populates="quotes")


class BookingStatusHistory(Base):
    """Append-only audit log of every booking status transition. Never updated
    or deleted after insert."""

    __tablename__ = "booking_status_history"
    __table_args__ = (
        CheckConstraint(
            f"from_status IS NULL OR {check_in('from_status', BookingStatus)}",
            name="from_status_valid",
        ),
        CheckConstraint(check_in("to_status", BookingStatus), name="to_status_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    booking: Mapped["Booking"] = relationship(back_populates="status_history")


class BookingAttachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "booking_attachments"
    __table_args__ = (
        CheckConstraint(check_in("file_type", AttachmentFileType), name="file_type_valid"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    file_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(255))

    booking: Mapped["Booking"] = relationship(back_populates="attachments")
