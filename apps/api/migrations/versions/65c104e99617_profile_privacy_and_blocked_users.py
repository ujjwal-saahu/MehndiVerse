"""profile: privacy preferences and blocked-user foundation

Adds privacy-related columns to `user_preferences` (`profile_visibility`,
`show_location`, `allow_messages_from_strangers`) and a new `user_blocks`
table for the self-service block/unblock foundation introduced in Phase 5.
See docs/profile-and-privacy.md.

Revision ID: 65c104e99617
Revises: 3f28fa5a570a
Create Date: 2026-07-14 21:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "65c104e99617"
down_revision: Union[str, Sequence[str], None] = "3f28fa5a570a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "profile_visibility",
            sa.String(length=20),
            nullable=False,
            server_default="public",
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "show_location",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "allow_messages_from_strangers",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.create_check_constraint(
        op.f("ck_user_preferences_profile_visibility_valid"),
        "user_preferences",
        "profile_visibility IN ('public', 'private')",
    )

    op.create_table(
        "user_blocks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("blocker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("blocked_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("blocker_id != blocked_id", name=op.f("ck_user_blocks_blocker_not_blocked")),
        sa.ForeignKeyConstraint(
            ["blocker_id"], ["users.id"], name=op.f("fk_user_blocks_blocker_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["blocked_id"], ["users.id"], name=op.f("fk_user_blocks_blocked_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_blocks")),
        sa.UniqueConstraint(
            "blocker_id", "blocked_id", name=op.f("uq_user_blocks_blocker_id_blocked_id")
        ),
    )
    op.create_index(op.f("ix_user_blocks_blocker_id"), "user_blocks", ["blocker_id"])
    op.create_index(op.f("ix_user_blocks_blocked_id"), "user_blocks", ["blocked_id"])

    # RLS foundation, consistent with migrations/versions/
    # 3f28fa5a570a_auth_row_level_security_foundations.py — a self-service
    # join row is only ever visible/manageable by the user who created it.
    op.execute("ALTER TABLE user_blocks ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY user_blocks_all_own ON user_blocks "
        "FOR ALL USING (blocker_id = auth.uid()) WITH CHECK (blocker_id = auth.uid())"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS user_blocks_all_own ON user_blocks")
    op.execute("ALTER TABLE user_blocks DISABLE ROW LEVEL SECURITY")
    op.drop_index(op.f("ix_user_blocks_blocked_id"), table_name="user_blocks")
    op.drop_index(op.f("ix_user_blocks_blocker_id"), table_name="user_blocks")
    op.drop_table("user_blocks")

    op.drop_constraint(
        op.f("ck_user_preferences_profile_visibility_valid"), "user_preferences", type_="check"
    )
    op.drop_column("user_preferences", "allow_messages_from_strangers")
    op.drop_column("user_preferences", "show_location")
    op.drop_column("user_preferences", "profile_visibility")
