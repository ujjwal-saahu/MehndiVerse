"""design search foundation: full-text search, save_count, search_events

Adds:
- `designs.search_vector` — a generated (STORED) tsvector over
  title+description, plus a GIN index for `@@` full-text queries.
- `designs.save_count` — a "most saved" sort foundation, mirroring the
  existing `view_count`/`like_count` denormalized-counter pattern, plus a
  composite keyset-pagination index matching the existing
  status/created_at/view_count ones.
- A functional btree index on `lower(title)` for prefix-match search
  suggestions (no pg_trgm dependency needed for a simple prefix match).
- `search_events` — the combined foundation for per-user "recent searches"
  and search analytics (see docs/design-search.md).

Revision ID: d71aff4fa47b
Revises: b225a8402428
Create Date: 2026-07-15 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d71aff4fa47b"
down_revision: Union[str, Sequence[str], None] = "b225a8402428"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "designs",
        sa.Column("save_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        op.f("ck_designs_save_count_non_negative"), "designs", "save_count >= 0"
    )
    op.create_index(
        op.f("ix_designs_status_save_count_id"), "designs", ["status", "save_count", "id"]
    )

    op.add_column(
        "designs",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))",
                persisted=True,
            ),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_designs_search_vector"), "designs", ["search_vector"], postgresql_using="gin"
    )
    op.create_index(
        op.f("ix_designs_title_lower_pattern"),
        "designs",
        [sa.text("lower(title) text_pattern_ops")],
    )

    op.create_table(
        "search_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query", sa.String(length=200), nullable=True),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "result_count >= 0", name=op.f("ck_search_events_result_count_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_search_events_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_search_events")),
    )
    op.create_index(
        op.f("ix_search_events_user_id_created_at"), "search_events", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_search_events_user_id_created_at"), table_name="search_events")
    op.drop_table("search_events")

    op.drop_index(op.f("ix_designs_title_lower_pattern"), table_name="designs")
    op.drop_index(op.f("ix_designs_search_vector"), table_name="designs")
    op.drop_column("designs", "search_vector")

    op.drop_index(op.f("ix_designs_status_save_count_id"), table_name="designs")
    op.drop_constraint(op.f("ck_designs_save_count_non_negative"), "designs", type_="check")
    op.drop_column("designs", "save_count")
