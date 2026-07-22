"""admin dashboard: promo banners, featured collections, notification campaigns

Phase 17. Three brand-new marketing/admin domains with no prior schema —
see docs/admin-dashboard.md#new-marketing-domains:

- `promo_banners`: homepage/marketing banners, staff-managed.
- `featured_collections` / `featured_collection_items`: staff-curated
  groups of designs for homepage merchandising — distinct from the
  pre-existing user-owned `collections`/`collection_items` (Phase 2).
- `notification_campaigns`: a record of a bulk notification staff sent (or
  drafted) to a role-targeted (or all) audience.

Revision ID: 7a448a982206
Revises: b28f4d6c9a3e
Create Date: 2026-07-16 14:54:32.574618

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a448a982206"
down_revision: str | Sequence[str] | None = "b28f4d6c9a3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "featured_collections",
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_image_url", sa.String(length=2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_featured_collections_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_featured_collections")),
    )
    op.create_table(
        "notification_campaigns",
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("target_role", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("recipient_count", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'sent')", name=op.f("ck_notification_campaigns_status_valid")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_notification_campaigns_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_campaigns")),
    )
    op.create_table(
        "promo_banners",
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("subtitle", sa.String(length=300), nullable=True),
        sa.Column("image_url", sa.String(length=2048), nullable=False),
        sa.Column("link_url", sa.String(length=2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_promo_banners_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_promo_banners")),
    )
    op.create_table(
        "featured_collection_items",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("featured_collection_id", sa.UUID(), nullable=False),
        sa.Column("design_id", sa.UUID(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["design_id"],
            ["designs.id"],
            name=op.f("fk_featured_collection_items_design_id_designs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["featured_collection_id"],
            ["featured_collections.id"],
            name=op.f("fk_featured_collection_items_featured_collection_id_featured_collections"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_featured_collection_items")),
        sa.UniqueConstraint(
            "featured_collection_id",
            "design_id",
            name="uq_featured_collection_items_collection_design",
        ),
    )
    op.create_index(
        op.f("ix_featured_collection_items_design_id"),
        "featured_collection_items",
        ["design_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_featured_collection_items_featured_collection_id"),
        "featured_collection_items",
        ["featured_collection_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_featured_collection_items_featured_collection_id"),
        table_name="featured_collection_items",
    )
    op.drop_index(
        op.f("ix_featured_collection_items_design_id"), table_name="featured_collection_items"
    )
    op.drop_table("featured_collection_items")
    op.drop_table("promo_banners")
    op.drop_table("notification_campaigns")
    op.drop_table("featured_collections")
