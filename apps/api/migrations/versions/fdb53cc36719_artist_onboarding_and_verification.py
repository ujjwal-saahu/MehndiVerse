"""artist onboarding and verification

Expands `artist_profiles` with onboarding fields (professional_name,
service_areas, languages, contact_email, contact_phone, social_links,
profile_image_url, cover_image_url) and a fuller verification lifecycle:
`verification_status` grows from 5 values (pending/under_review/verified/
rejected/suspended) to 7 (draft/submitted/under_review/
more_information_required/approved/rejected/suspended) — see
docs/artist-verification.md#verification-lifecycle. `verified_at`/
`verified_by` are replaced by `submitted_at`/`reviewed_at`/`reviewed_by`
(the latter two reflect the *last* staff action of any kind, not just
approval) plus `rejection_reason`/`more_info_request`.

`artist_documents.file_url` becomes `storage_path` — a bucket-relative path
in the private `verification-documents` bucket rather than a durable URL,
since signed URLs are minted on demand at read time (see
docs/artist-verification.md#document-privacy). Adds `original_filename`,
`content_type`, `file_size_bytes`; both new NOT NULL columns are safe to add
without a server_default since no upload endpoint has ever written to this
table before this phase.

Revision ID: fdb53cc36719
Revises: 12759e9f3128
Create Date: 2026-07-17 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fdb53cc36719"
down_revision: Union[str, Sequence[str], None] = "12759e9f3128"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_STATUS_TO_NEW = {
    "pending": "draft",
    "under_review": "under_review",
    "verified": "approved",
    "rejected": "rejected",
    "suspended": "suspended",
}


def upgrade() -> None:
    # --- artist_profiles: onboarding fields ---------------------------------
    op.add_column("artist_profiles", sa.Column("professional_name", sa.String(150), nullable=True))
    op.add_column("artist_profiles", sa.Column("service_areas", postgresql.JSONB(), nullable=True))
    op.add_column("artist_profiles", sa.Column("languages", postgresql.JSONB(), nullable=True))
    op.add_column("artist_profiles", sa.Column("contact_email", sa.String(255), nullable=True))
    op.add_column("artist_profiles", sa.Column("contact_phone", sa.String(30), nullable=True))
    op.add_column("artist_profiles", sa.Column("social_links", postgresql.JSONB(), nullable=True))
    op.add_column("artist_profiles", sa.Column("profile_image_url", sa.String(2048), nullable=True))
    op.add_column("artist_profiles", sa.Column("cover_image_url", sa.String(2048), nullable=True))

    # --- artist_profiles: verification lifecycle rework ---------------------
    # The RLS policy from migrations/versions/3f28fa5a570a depends on
    # verification_status (`... verification_status = 'verified' ...`), so
    # Postgres refuses to ALTER COLUMN TYPE while it exists. Drop it first and
    # recreate it after — with 'verified' corrected to 'approved', since that
    # migration predates this phase's rename (see
    # app/db/enums.py::ArtistVerificationStatus).
    op.execute(
        "DROP POLICY IF EXISTS artist_profiles_select_verified_own_or_staff ON artist_profiles"
    )

    op.drop_constraint(
        op.f("ck_artist_profiles_verification_status_valid"), "artist_profiles", type_="check"
    )
    op.alter_column(
        "artist_profiles", "verification_status", type_=sa.String(30), existing_nullable=False
    )
    artist_profiles = sa.table("artist_profiles", sa.column("verification_status", sa.String))
    for old_value, new_value in _OLD_STATUS_TO_NEW.items():
        op.execute(
            artist_profiles.update()
            .where(artist_profiles.c.verification_status == old_value)
            .values(verification_status=new_value)
        )
    op.alter_column(
        "artist_profiles",
        "verification_status",
        server_default="draft",
        existing_type=sa.String(30),
        existing_nullable=False,
    )
    op.create_check_constraint(
        op.f("ck_artist_profiles_verification_status_valid"),
        "artist_profiles",
        "verification_status IN ('draft', 'submitted', 'under_review', "
        "'more_information_required', 'approved', 'rejected', 'suspended')",
    )

    op.execute(
        "CREATE POLICY artist_profiles_select_verified_own_or_staff ON artist_profiles "
        "FOR SELECT USING ("
        "verification_status = 'approved' OR user_id = auth.uid() OR app_is_staff()"
        ")"
    )

    op.add_column(
        "artist_profiles", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "artist_profiles", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "artist_profiles",
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_artist_profiles_reviewed_by_users"),
        "artist_profiles",
        "users",
        ["reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("artist_profiles", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.add_column("artist_profiles", sa.Column("more_info_request", sa.Text(), nullable=True))

    op.drop_constraint(
        op.f("fk_artist_profiles_verified_by_users"), "artist_profiles", type_="foreignkey"
    )
    op.drop_column("artist_profiles", "verified_by")
    op.drop_column("artist_profiles", "verified_at")

    # --- artist_documents: private storage path + upload metadata ----------
    op.alter_column("artist_documents", "file_url", new_column_name="storage_path")
    op.add_column("artist_documents", sa.Column("original_filename", sa.String(255), nullable=True))
    op.add_column("artist_documents", sa.Column("content_type", sa.String(100), nullable=False))
    op.add_column("artist_documents", sa.Column("file_size_bytes", sa.Integer(), nullable=False))
    op.create_check_constraint(
        op.f("ck_artist_documents_file_size_bytes_positive"),
        "artist_documents",
        "file_size_bytes > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_artist_documents_file_size_bytes_positive"), "artist_documents", type_="check"
    )
    op.drop_column("artist_documents", "file_size_bytes")
    op.drop_column("artist_documents", "content_type")
    op.drop_column("artist_documents", "original_filename")
    op.alter_column("artist_documents", "storage_path", new_column_name="file_url")

    op.add_column(
        "artist_profiles", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "artist_profiles",
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_artist_profiles_verified_by_users"),
        "artist_profiles",
        "users",
        ["verified_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_column("artist_profiles", "more_info_request")
    op.drop_column("artist_profiles", "rejection_reason")
    op.drop_constraint(
        op.f("fk_artist_profiles_reviewed_by_users"), "artist_profiles", type_="foreignkey"
    )
    op.drop_column("artist_profiles", "reviewed_by")
    op.drop_column("artist_profiles", "reviewed_at")
    op.drop_column("artist_profiles", "submitted_at")

    op.execute(
        "DROP POLICY IF EXISTS artist_profiles_select_verified_own_or_staff ON artist_profiles"
    )

    op.drop_constraint(
        op.f("ck_artist_profiles_verification_status_valid"), "artist_profiles", type_="check"
    )
    artist_profiles = sa.table("artist_profiles", sa.column("verification_status", sa.String))
    # The two new mid-flow statuses have no equivalent in the old 5-value
    # enum — collapse to the closest fit (draft/submitted -> pending,
    # more_information_required -> under_review) rather than fail.
    _NEW_STATUS_TO_OLD = {
        "draft": "pending",
        "submitted": "pending",
        "under_review": "under_review",
        "more_information_required": "under_review",
        "approved": "verified",
        "rejected": "rejected",
        "suspended": "suspended",
    }
    for new_value, old_value in _NEW_STATUS_TO_OLD.items():
        op.execute(
            artist_profiles.update()
            .where(artist_profiles.c.verification_status == new_value)
            .values(verification_status=old_value)
        )
    op.alter_column(
        "artist_profiles",
        "verification_status",
        server_default="pending",
        existing_type=sa.String(30),
        existing_nullable=False,
    )
    op.alter_column(
        "artist_profiles", "verification_status", type_=sa.String(20), existing_nullable=False
    )
    op.create_check_constraint(
        op.f("ck_artist_profiles_verification_status_valid"),
        "artist_profiles",
        "verification_status IN ('pending', 'under_review', 'verified', 'rejected', 'suspended')",
    )
    op.execute(
        "CREATE POLICY artist_profiles_select_verified_own_or_staff ON artist_profiles "
        "FOR SELECT USING ("
        "verification_status = 'verified' OR user_id = auth.uid() OR app_is_staff()"
        ")"
    )

    op.drop_column("artist_profiles", "cover_image_url")
    op.drop_column("artist_profiles", "profile_image_url")
    op.drop_column("artist_profiles", "social_links")
    op.drop_column("artist_profiles", "contact_phone")
    op.drop_column("artist_profiles", "contact_email")
    op.drop_column("artist_profiles", "languages")
    op.drop_column("artist_profiles", "service_areas")
    op.drop_column("artist_profiles", "professional_name")
