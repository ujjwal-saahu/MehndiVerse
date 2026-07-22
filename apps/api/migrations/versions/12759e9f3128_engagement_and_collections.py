"""engagement and collections: cover pick, item ordering, one default per user

Adds, on top of the `likes`/`collections`/`collection_items` tables already
created in Phase 2:
- `collections.cover_design_id` — an explicit cover pick (falls back to the
  most recently added item at read time when unset).
- A partial unique index guaranteeing at most one `is_default=true`
  collection per user (the "Saved" bucket `POST /designs/{id}/save`
  get-or-creates) — see docs/engagement-and-collections.md.
- `collection_items.sort_order` — manual drag-order within a collection,
  plus a composite index for ordered listing.

Revision ID: 12759e9f3128
Revises: d71aff4fa47b
Create Date: 2026-07-16 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "12759e9f3128"
down_revision: Union[str, Sequence[str], None] = "d71aff4fa47b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "collections",
        sa.Column("cover_design_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_collections_cover_design_id"), "collections", ["cover_design_id"]
    )
    op.create_foreign_key(
        op.f("fk_collections_cover_design_id_designs"),
        "collections",
        "designs",
        ["cover_design_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_collections_one_default_per_user",
        "collections",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )

    op.add_column(
        "collection_items",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        op.f("ix_collection_items_collection_id_sort_order"),
        "collection_items",
        ["collection_id", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_collection_items_collection_id_sort_order"), table_name="collection_items"
    )
    op.drop_column("collection_items", "sort_order")

    op.drop_index("uq_collections_one_default_per_user", table_name="collections")
    op.drop_constraint(
        op.f("fk_collections_cover_design_id_designs"), "collections", type_="foreignkey"
    )
    op.drop_index(op.f("ix_collections_cover_design_id"), table_name="collections")
    op.drop_column("collections", "cover_design_id")
