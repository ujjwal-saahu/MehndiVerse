"""moderation queue duplicate-report guard

Phase 16. Adds a partial unique index on `reports` so the same reporter
cannot open a second *pending* report against the same target — see
docs/community-and-trust.md#7-abuse-prevention. Mirrors the
`uq_collections_one_default_per_user` partial-unique-index pattern (Phase 6)
rather than a plain unique constraint, since a reporter legitimately may
report the same target again *after* an earlier report on it has been
resolved/dismissed — only concurrently-open (pending) duplicates are
rejected.

Revision ID: b28f4d6c9a3e
Revises: a7c3e9d15f2a
Create Date: 2026-08-09 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b28f4d6c9a3e"
down_revision: str | Sequence[str] | None = "a7c3e9d15f2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_reports_one_pending_per_reporter_and_target",
        "reports",
        ["reporter_id", "reported_entity_type", "reported_entity_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("uq_reports_one_pending_per_reporter_and_target", table_name="reports")
