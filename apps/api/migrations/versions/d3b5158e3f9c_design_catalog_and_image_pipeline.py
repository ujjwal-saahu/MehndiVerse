"""design catalog: category taxonomy, premium designs, image upload pipeline

Adds `categories.category_type` (the style/occasion/body_part/difficulty/
density/region taxonomy axis), `designs.is_premium`, and the
pending -> processing -> ready|failed upload-pipeline columns on
`design_images`. See docs/design-catalog.md.

`category_type` is backfilled for the ten categories seeded in
a4708e2fb0ee_seed_basic_categories before being made NOT NULL — see
docs/migration-guidelines.md on backfilling before tightening a constraint.
New categories are seeded for the three taxonomy axes that had no prior
representation (difficulty, density, region).

Revision ID: d3b5158e3f9c
Revises: 65c104e99617
Create Date: 2026-07-14 22:00:00.000000

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3b5158e3f9c"
down_revision: Union[str, Sequence[str], None] = "65c104e99617"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

categories_table = sa.table(
    "categories",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("slug", sa.String),
    sa.column("category_type", sa.String),
    sa.column("description", sa.String),
    sa.column("sort_order", sa.SmallInteger),
    sa.column("is_active", sa.Boolean),
)

# slug -> category_type for the ten categories seeded in a4708e2fb0ee.
_EXISTING_CATEGORY_TYPES: dict[str, str] = {
    "bridal": "occasion",
    "arabic": "style",
    "indian-traditional": "style",
    "moroccan": "style",
    "floral": "style",
    "geometric": "style",
    "minimalist": "style",
    "full-hand": "body_part",
    "full-foot": "body_part",
    "kids": "occasion",
}

# (name, slug, category_type, description, sort_order)
_NEW_CATEGORIES: list[tuple[str, str, str, str, int]] = [
    ("Beginner Friendly", "beginner-friendly", "difficulty", "Simple patterns, quick to apply.", 0),
    ("Intermediate", "intermediate", "difficulty", "Moderate detail and application time.", 1),
    ("Advanced", "advanced", "difficulty", "Intricate, time-intensive patterns.", 2),
    ("Light Coverage", "light-coverage", "density", "Sparse, airy patterns with open space.", 0),
    ("Medium Coverage", "medium-coverage", "density", "Balanced pattern density.", 1),
    ("Heavy Coverage", "heavy-coverage", "density", "Dense, richly filled patterns.", 2),
    ("North Indian", "north-indian", "region", "Patterns associated with North Indian style.", 0),
    ("South Indian", "south-indian", "region", "Patterns associated with South Indian style.", 1),
    ("Middle Eastern", "middle-eastern", "region", "Patterns associated with Middle Eastern style.", 2),
    ("North African", "north-african", "region", "Patterns associated with North African style.", 3),
]


def upgrade() -> None:
    op.add_column("categories", sa.Column("category_type", sa.String(length=20), nullable=True))
    for slug, category_type in _EXISTING_CATEGORY_TYPES.items():
        op.execute(
            categories_table.update()
            .where(categories_table.c.slug == slug)
            .values(category_type=category_type)
        )
    op.alter_column("categories", "category_type", nullable=False)
    op.create_check_constraint(
        op.f("ck_categories_category_type_valid"),
        "categories",
        "category_type IN ('style', 'occasion', 'body_part', 'difficulty', 'density', 'region')",
    )
    op.create_index(
        op.f("ix_categories_category_type"), "categories", ["category_type"]
    )

    op.bulk_insert(
        categories_table,
        [
            {
                "id": uuid.uuid4(),
                "name": name,
                "slug": slug,
                "category_type": category_type,
                "description": description,
                "sort_order": sort_order,
                "is_active": True,
            }
            for name, slug, category_type, description, sort_order in _NEW_CATEGORIES
        ],
    )

    op.add_column(
        "designs",
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(op.f("ix_designs_status"), "designs", ["status"])

    op.add_column(
        "design_images",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
    )
    op.alter_column("design_images", "image_url", existing_type=sa.String(length=2048), nullable=True)
    op.add_column(
        "design_images", sa.Column("thumbnail_small_url", sa.String(length=2048), nullable=True)
    )
    op.add_column(
        "design_images", sa.Column("thumbnail_medium_url", sa.String(length=2048), nullable=True)
    )
    op.add_column("design_images", sa.Column("storage_path", sa.String(length=2048), nullable=True))
    op.add_column(
        "design_images", sa.Column("original_filename", sa.String(length=255), nullable=True)
    )
    op.add_column("design_images", sa.Column("mime_type", sa.String(length=100), nullable=True))
    op.add_column("design_images", sa.Column("file_size_bytes", sa.Integer(), nullable=True))
    op.add_column(
        "design_images", sa.Column("checksum_sha256", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "design_images", sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        "design_images", sa.Column("processing_error", sa.String(length=500), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_design_images_uploaded_by_users"),
        "design_images",
        "users",
        ["uploaded_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        op.f("ck_design_images_status_valid"),
        "design_images",
        "status IN ('pending', 'processing', 'ready', 'failed')",
    )
    op.create_check_constraint(
        op.f("ck_design_images_file_size_bytes_non_negative"),
        "design_images",
        "file_size_bytes IS NULL OR file_size_bytes >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_design_images_file_size_bytes_non_negative"), "design_images", type_="check"
    )
    op.drop_constraint(op.f("ck_design_images_status_valid"), "design_images", type_="check")
    op.drop_constraint(
        op.f("fk_design_images_uploaded_by_users"), "design_images", type_="foreignkey"
    )
    op.drop_column("design_images", "processing_error")
    op.drop_column("design_images", "uploaded_by")
    op.drop_column("design_images", "checksum_sha256")
    op.drop_column("design_images", "file_size_bytes")
    op.drop_column("design_images", "mime_type")
    op.drop_column("design_images", "original_filename")
    op.drop_column("design_images", "storage_path")
    op.drop_column("design_images", "thumbnail_medium_url")
    op.drop_column("design_images", "thumbnail_small_url")
    op.alter_column("design_images", "image_url", existing_type=sa.String(length=2048), nullable=False)
    op.drop_column("design_images", "status")

    op.drop_index(op.f("ix_designs_status"), table_name="designs")
    op.drop_column("designs", "is_premium")

    op.execute(
        categories_table.delete().where(
            categories_table.c.slug.in_([slug for _, slug, _, _, _ in _NEW_CATEGORIES])
        )
    )
    op.drop_index(op.f("ix_categories_category_type"), table_name="categories")
    op.drop_constraint(op.f("ck_categories_category_type_valid"), "categories", type_="check")
    op.drop_column("categories", "category_type")
