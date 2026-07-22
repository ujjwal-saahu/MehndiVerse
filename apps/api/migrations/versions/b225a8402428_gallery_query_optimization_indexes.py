"""gallery: query-optimization indexes for the customer design gallery

Replaces the single-column `ix_designs_status` index with three composite,
keyset-pagination-friendly indexes powering the Phase 7 home-feed sections
(latest/featured/trending) and adds an index on
`design_categories.category_id` for category browsing (the composite PK on
that table only indexes `design_id` as its leading column). See
docs/design-gallery.md#query-optimization.

Revision ID: b225a8402428
Revises: d3b5158e3f9c
Create Date: 2026-07-14 23:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b225a8402428"
down_revision: Union[str, Sequence[str], None] = "d3b5158e3f9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_designs_status"), table_name="designs")
    op.create_index(
        op.f("ix_designs_status_created_at_id"), "designs", ["status", "created_at", "id"]
    )
    op.create_index(
        op.f("ix_designs_status_is_featured_created_at"),
        "designs",
        ["status", "is_featured", "created_at"],
    )
    op.create_index(
        op.f("ix_designs_status_view_count_id"), "designs", ["status", "view_count", "id"]
    )
    op.create_index(
        op.f("ix_design_categories_category_id"), "design_categories", ["category_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_design_categories_category_id"), table_name="design_categories")
    op.drop_index(op.f("ix_designs_status_view_count_id"), table_name="designs")
    op.drop_index(op.f("ix_designs_status_is_featured_created_at"), table_name="designs")
    op.drop_index(op.f("ix_designs_status_created_at_id"), table_name="designs")
    op.create_index(op.f("ix_designs_status"), "designs", ["status"])
