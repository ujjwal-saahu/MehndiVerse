"""seed basic categories

A data-only migration (see docs/migration-guidelines.md#schema-vs-data-migrations)
that seeds the initial design category taxonomy.

Note on "roles" seed data: user roles are not a separate table — they are
enforced via a CHECK constraint on `users.role` (see docs/database-schema.md
#enum-strategy and app/db/enums.py::UserRole). There is nothing to seed for
roles; the enum values themselves are the "seed data".

Revision ID: a4708e2fb0ee
Revises: 8dab12dd6727
Create Date: 2026-07-14 16:06:09.876308

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4708e2fb0ee"
down_revision: Union[str, Sequence[str], None] = "8dab12dd6727"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

categories_table = sa.table(
    "categories",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("slug", sa.String),
    sa.column("description", sa.String),
    sa.column("sort_order", sa.SmallInteger),
    sa.column("is_active", sa.Boolean),
)

# (name, slug, description, sort_order)
CATEGORIES: list[tuple[str, str, str, int]] = [
    ("Bridal", "bridal", "Elaborate designs for weddings and bridal ceremonies.", 0),
    ("Arabic", "arabic", "Bold floral and vine patterns with open spacing.", 1),
    (
        "Indian Traditional",
        "indian-traditional",
        "Dense traditional Indian motifs and patterns.",
        2,
    ),
    ("Moroccan", "moroccan", "Geometric patterns inspired by Moroccan art.", 3),
    ("Floral", "floral", "Designs centered on flower and leaf motifs.", 4),
    ("Geometric", "geometric", "Patterns built from repeating geometric shapes.", 5),
    ("Minimalist", "minimalist", "Simple, delicate designs with light coverage.", 6),
    ("Full Hand", "full-hand", "Designs covering the full hand and forearm.", 7),
    ("Full Foot", "full-foot", "Designs covering the full foot and ankle.", 8),
    ("Kids", "kids", "Simple, quick designs suited for children.", 9),
]


def upgrade() -> None:
    op.bulk_insert(
        categories_table,
        [
            {
                "id": uuid.uuid4(),
                "name": name,
                "slug": slug,
                "description": description,
                "sort_order": sort_order,
                "is_active": True,
            }
            for name, slug, description, sort_order in CATEGORIES
        ],
    )


def downgrade() -> None:
    slugs = [slug for _, slug, _, _ in CATEGORIES]
    op.execute(categories_table.delete().where(categories_table.c.slug.in_(slugs)))
