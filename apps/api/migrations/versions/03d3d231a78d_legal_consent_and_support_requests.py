"""legal consent and support requests

Three tables for Phase 29 (legal, privacy, and customer-support
foundation) — see docs/legal-and-support.md. `consent_records` and
`data_export_requests` are append-only compliance evidence (RESTRICT on
delete: a real user row is never hard-deleted, only anonymized in place —
see app/services/account_deletion.py — so this FK is never actually
exercised, but RESTRICT is the correct intent regardless).
`support_requests` allows a NULL `user_id` (SET NULL on delete) since a
signed-out visitor can submit one.

Revision ID: 03d3d231a78d
Revises: 8f509ffde693
Create Date: 2026-07-21 23:58:43.197696

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "03d3d231a78d"
down_revision: str | Sequence[str] | None = "8f509ffde693"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consent_records",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("consent_type", sa.String(length=30), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "consent_type IN ('terms_of_service', 'privacy_policy', 'cookies_analytics')",
            name=op.f("ck_consent_records_consent_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_consent_records_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consent_records")),
    )
    op.create_index(
        op.f("ix_consent_records_consent_type"), "consent_records", ["consent_type"], unique=False
    )
    op.create_index(
        op.f("ix_consent_records_user_id"), "consent_records", ["user_id"], unique=False
    )

    op.create_table(
        "data_export_requests",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_data_export_requests_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_export_requests")),
    )
    op.create_index(
        op.f("ix_data_export_requests_user_id"), "data_export_requests", ["user_id"], unique=False
    )

    op.create_table(
        "support_requests",
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "category IN ('bug_report', 'account_issue', 'billing_issue', 'artist_issue', 'other')",
            name=op.f("ck_support_requests_support_category_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('open', 'resolved')", name=op.f("ck_support_requests_support_status_valid")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_support_requests_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_support_requests")),
    )
    op.create_index(
        op.f("ix_support_requests_category"), "support_requests", ["category"], unique=False
    )
    op.create_index(
        op.f("ix_support_requests_status"), "support_requests", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_support_requests_user_id"), "support_requests", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_support_requests_user_id"), table_name="support_requests")
    op.drop_index(op.f("ix_support_requests_status"), table_name="support_requests")
    op.drop_index(op.f("ix_support_requests_category"), table_name="support_requests")
    op.drop_table("support_requests")
    op.drop_index(op.f("ix_data_export_requests_user_id"), table_name="data_export_requests")
    op.drop_table("data_export_requests")
    op.drop_index(op.f("ix_consent_records_user_id"), table_name="consent_records")
    op.drop_index(op.f("ix_consent_records_consent_type"), table_name="consent_records")
    op.drop_table("consent_records")
