"""hand/foot design preview

Phase 19. `preview_projects.source_image_url`/`result_image_url` are
renamed to `source_storage_path`/`result_storage_path` and repurposed to
hold bucket-relative paths in the new private `preview-projects` bucket
instead of durable URLs — these are real photos of a customer's hand/foot,
not marketing content, so they get the same "no public URL, mint a signed
one on demand" treatment `artist_documents.storage_path` already has (see
docs/hand-foot-preview.md). New columns: `source_width`/`source_height`
(so a client can resume editing without re-measuring the photo),
`overlay_transform` (JSONB — the design overlay's position/scale/rotation/
flip/opacity), and `shared_with_booking_id` (set by "send to artist",
grants that booking's artist read access to this one preview).

Revision ID: a1b2c3d4e5f6
Revises: f1c8a37e5b04
Create Date: 2026-07-21 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "f1c8a37e5b04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("preview_projects", "source_image_url", new_column_name="source_storage_path")
    op.alter_column("preview_projects", "result_image_url", new_column_name="result_storage_path")
    op.add_column("preview_projects", sa.Column("source_width", sa.Integer(), nullable=True))
    op.add_column("preview_projects", sa.Column("source_height", sa.Integer(), nullable=True))
    op.add_column(
        "preview_projects",
        sa.Column("overlay_transform", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "preview_projects",
        sa.Column("shared_with_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_preview_projects_shared_with_booking_id_bookings"),
        "preview_projects",
        "bookings",
        ["shared_with_booking_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_preview_projects_shared_with_booking_id",
        "preview_projects",
        ["shared_with_booking_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_preview_projects_shared_with_booking_id", table_name="preview_projects")
    op.drop_constraint(
        op.f("fk_preview_projects_shared_with_booking_id_bookings"),
        "preview_projects",
        type_="foreignkey",
    )
    op.drop_column("preview_projects", "shared_with_booking_id")
    op.drop_column("preview_projects", "overlay_transform")
    op.drop_column("preview_projects", "source_height")
    op.drop_column("preview_projects", "source_width")
    op.alter_column("preview_projects", "result_storage_path", new_column_name="result_image_url")
    op.alter_column("preview_projects", "source_storage_path", new_column_name="source_image_url")
