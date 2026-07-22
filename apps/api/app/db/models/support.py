import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import (
    ConsentType,
    SupportRequestCategory,
    SupportRequestStatus,
    check_in,
)
from app.db.mixins import UUIDPrimaryKeyMixin


class ConsentRecord(UUIDPrimaryKeyMixin, Base):
    """Append-only — a consent decision is evidence of what happened at a
    point in time, never edited or deleted. See docs/legal-and-support.md
    #consent-records. `user_id` uses ON DELETE RESTRICT: a compliance record
    must never silently disappear, and in practice it never needs to — the
    account-deletion flow (app/services/account_deletion.py) anonymizes the
    `User` row in place rather than deleting it, so this FK is never actually
    exercised."""

    __tablename__ = "consent_records"
    __table_args__ = (
        CheckConstraint(check_in("consent_type", ConsentType), name="consent_type_valid"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    consent_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SupportRequest(UUIDPrimaryKeyMixin, Base):
    """Backs both "Report a problem" and "Contact support" — both are just a
    free-text message plus a category, triaged by staff the same way; see
    docs/legal-and-support.md#report-a-problem-and-contact-support. Distinct
    from app/db/models/moderation.py::Report, which reports a specific piece
    of content/another user for moderation, not a product/account problem.
    `user_id` is nullable — a signed-out visitor can still contact support,
    identified only by the email they typed in."""

    __tablename__ = "support_requests"
    __table_args__ = (
        CheckConstraint(
            check_in("category", SupportRequestCategory), name="support_category_valid"
        ),
        CheckConstraint(check_in("status", SupportRequestStatus), name="support_status_valid"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SupportRequestStatus.OPEN.value, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DataExportRequest(UUIDPrimaryKeyMixin, Base):
    """Audit-only row: proof that a data-export was requested/served, and
    when. The export payload itself is generated on demand and never stored
    at rest — storing a second copy of a full personal-data export would
    itself be a new data-retention liability. See docs/legal-and-support.md
    #data-export-request."""

    __tablename__ = "data_export_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
