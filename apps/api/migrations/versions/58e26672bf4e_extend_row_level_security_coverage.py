"""extend row level security coverage

Phase 24 security review: `3f28fa5a570a_auth_row_level_security_foundations`
(Phase 14) covered a representative first slice of tables (users, profiles,
designs, bookings, messages, notifications, payments, ...). Every table
added by a later phase — conversations, reviews, collections,
subscriptions, reports, preview_projects, ai_generations, audit_logs — had
no RLS at all, leaving the "defense-in-depth for direct Supabase-mediated
access" guarantee in docs/security-baseline.md#2 unmet for them. This is
the same defense-in-depth backstop as before: the FastAPI RBAC layer
remains the primary authorization mechanism and is unaffected (the
application's own DB role owns these tables and bypasses RLS).

See docs/security-review.md#row-level-security for the full audit.

Revision ID: 58e26672bf4e
Revises: 3e799ebff530
Create Date: 2026-07-21 20:03:07.291625

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58e26672bf4e"
down_revision: str | Sequence[str] | None = "3e799ebff530"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, [policy statements]) — same shape/convention as
# 3f28fa5a570a_auth_row_level_security_foundations.py.
_POLICIES: list[tuple[str, list[str]]] = [
    (
        "conversations",
        [
            "CREATE POLICY conversations_select_member_or_staff ON conversations "
            "FOR SELECT USING ("
            "app_is_staff() "
            "OR EXISTS ("
            "SELECT 1 FROM conversation_members cm "
            "WHERE cm.conversation_id = conversations.id AND cm.user_id = auth.uid()"
            ")"
            ")",
        ],
    ),
    (
        "conversation_members",
        [
            "CREATE POLICY conversation_members_select_self_or_staff ON conversation_members "
            "FOR SELECT USING (user_id = auth.uid() OR app_is_staff())",
        ],
    ),
    (
        "reviews",
        [
            "CREATE POLICY reviews_select_public_or_author_or_staff ON reviews "
            "FOR SELECT USING (deleted_at IS NULL OR customer_id = auth.uid() OR app_is_staff())",
            "CREATE POLICY reviews_insert_own ON reviews "
            "FOR INSERT WITH CHECK (customer_id = auth.uid())",
        ],
    ),
    (
        "collections",
        [
            "CREATE POLICY collections_all_own_or_staff ON collections "
            "FOR ALL USING (user_id = auth.uid() OR app_is_staff()) "
            "WITH CHECK (user_id = auth.uid())",
        ],
    ),
    (
        "subscriptions",
        [
            "CREATE POLICY subscriptions_select_own_or_staff ON subscriptions "
            "FOR SELECT USING (user_id = auth.uid() OR app_is_staff())",
        ],
    ),
    (
        "reports",
        [
            "CREATE POLICY reports_select_own_or_staff ON reports "
            "FOR SELECT USING (reporter_id = auth.uid() OR app_is_staff())",
            "CREATE POLICY reports_insert_own ON reports "
            "FOR INSERT WITH CHECK (reporter_id = auth.uid())",
        ],
    ),
    (
        "preview_projects",
        [
            "CREATE POLICY preview_projects_all_own_or_staff ON preview_projects "
            "FOR ALL USING (user_id = auth.uid() OR app_is_staff()) "
            "WITH CHECK (user_id = auth.uid())",
        ],
    ),
    (
        "ai_generations",
        [
            "CREATE POLICY ai_generations_select_own_or_staff ON ai_generations "
            "FOR SELECT USING (user_id = auth.uid() OR app_is_staff())",
        ],
    ),
    (
        "ai_design_requests",
        [
            "CREATE POLICY ai_design_requests_select_own_or_staff ON ai_design_requests "
            "FOR SELECT USING (user_id = auth.uid() OR app_is_staff())",
        ],
    ),
    (
        "audit_logs",
        [
            # Staff-read only — no INSERT/UPDATE/DELETE policy at all, for
            # anyone. The application writes audit_logs exclusively through
            # its own DB role (which bypasses RLS, same as everywhere
            # else); this table should never be writable via a
            # Supabase-mediated client path under any circumstance.
            "CREATE POLICY audit_logs_select_staff_only ON audit_logs "
            "FOR SELECT USING (app_is_staff())",
        ],
    ),
]


def upgrade() -> None:
    for table, _ in _POLICIES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    for _, statements in _POLICIES:
        for statement in statements:
            op.execute(statement)


def downgrade() -> None:
    for table, statements in reversed(_POLICIES):
        for statement in statements:
            policy_name = statement.split(" ON ")[0].removeprefix("CREATE POLICY ").strip()
            op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
