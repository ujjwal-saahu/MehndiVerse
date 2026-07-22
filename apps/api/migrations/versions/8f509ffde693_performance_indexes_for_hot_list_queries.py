"""performance indexes for hot list queries

Phase 25 perf review: three list endpoints filter on one column and sort
by `created_at DESC` with a LIMIT, but only had a single-column index on
the filter column — each needs a separate sort pass instead of an ordered
index scan. Evidence (queries these composite indexes target):

- GET /bookings/mine            -> app/api/routes/bookings.py:99-105
- GET /bookings/{id}/conversation/messages -> app/api/routes/messaging.py:129-142
- GET /notifications             -> app/api/routes/notifications.py:62-77

The existing single-column indexes are left in place (other queries, e.g.
unread-count and mark-all-read, filter without the sort and still use them).

Revision ID: 8f509ffde693
Revises: 58e26672bf4e
Create Date: 2026-07-21 21:00:59.095849

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "8f509ffde693"
down_revision: Union[str, Sequence[str], None] = "58e26672bf4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEXES = [
    ("ix_bookings_customer_id_created_at", "bookings", ["customer_id", "created_at"]),
    ("ix_messages_conversation_id_created_at", "messages", ["conversation_id", "created_at"]),
    ("ix_notifications_user_id_created_at", "notifications", ["user_id", "created_at"]),
]


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        op.create_index(name, table, columns)


def downgrade() -> None:
    for name, table, _ in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
