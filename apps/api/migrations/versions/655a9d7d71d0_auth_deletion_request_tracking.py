"""auth: deletion request tracking

Adds `users.deletion_requested_at` and the `pending_deletion` status value,
supporting the self-service account-deletion request flow (Phase 3). See
docs/migration-guidelines.md#5-constraint-changes for why the CHECK
constraint is dropped and recreated rather than altered in place.

Revision ID: 655a9d7d71d0
Revises: a4708e2fb0ee
Create Date: 2026-07-14 16:43:43.089049

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "655a9d7d71d0"
down_revision: Union[str, Sequence[str], None] = "a4708e2fb0ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_STATUSES = "'active', 'suspended', 'deactivated'"
_NEW_STATUSES = "'active', 'suspended', 'deactivated', 'pending_deletion'"


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.drop_constraint(op.f("ck_users_status_valid"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users_status_valid"), "users", f"status IN ({_NEW_STATUSES})"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_users_status_valid"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users_status_valid"), "users", f"status IN ({_OLD_STATUSES})"
    )
    op.drop_column("users", "deletion_requested_at")
