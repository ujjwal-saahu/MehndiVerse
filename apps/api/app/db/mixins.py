import uuid
from datetime import datetime

from sqlalchemy import DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class UUIDPrimaryKeyMixin:
    """UUID v4 primary key generated server-side by Postgres (gen_random_uuid())."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    """created_at/updated_at as timestamptz (UTC internally, per Postgres semantics).

    updated_at is refreshed by SQLAlchemy (onupdate) for ORM-issued UPDATEs. Bulk/raw
    SQL updates that bypass the ORM will not refresh it — see docs/database-schema.md.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Nullable deleted_at marks a row as soft-deleted without removing it.

    Only applied to models where end-users can "delete" something that should
    remain recoverable/auditable (see docs/database-schema.md#soft-deletion-policy).
    Never applied to financial or audit-trail tables.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
