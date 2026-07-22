"""auth: row level security foundations

Enables Postgres Row-Level Security and adds baseline policies on a
representative set of tables, per docs/authentication.md#4. This is a
defense-in-depth backstop for direct Supabase-mediated access (Storage, or a
future direct-to-Postgres client read) — the FastAPI RBAC layer
(app/api/deps.py) is the primary authorization mechanism and is unaffected by
this migration, because the application's own DB role owns these tables and
table owners bypass RLS by default (no FORCE ROW LEVEL SECURITY is set).

On a real Supabase project, `auth.uid()` already exists (reads the caller's
JWT `sub` claim) and PostgREST connects as the `authenticated`/`anon` Postgres
roles. Locally (a vanilla `postgres:16-alpine` container, no Supabase
extensions), neither exists — this migration installs a functionally
identical `auth.uid()` shim *only if one isn't already present*, so the
policies below are exercisable and testable in local/CI Postgres without
touching a real project's own definition.

Revision ID: 3f28fa5a570a
Revises: 655a9d7d71d0
Create Date: 2026-07-14 16:47:23.122636

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f28fa5a570a"
down_revision: Union[str, Sequence[str], None] = "655a9d7d71d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_AUTH_UID_SHIM = """
DO $$
BEGIN
    IF to_regprocedure('auth.uid()') IS NULL THEN
        CREATE SCHEMA IF NOT EXISTS auth;
        CREATE FUNCTION auth.uid() RETURNS uuid
            LANGUAGE sql STABLE
            AS $fn$
                SELECT
                    COALESCE(
                        NULLIF(current_setting('request.jwt.claim.sub', true), ''),
                        (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
                    )::uuid
            $fn$;
    END IF;
END
$$;
"""

_HELPER_FUNCTIONS = """
CREATE OR REPLACE FUNCTION app_is_staff() RETURNS boolean
    LANGUAGE sql STABLE
    AS $$
        SELECT EXISTS (
            SELECT 1 FROM users
            WHERE id = auth.uid()
            AND role IN ('moderator', 'administrator', 'super_administrator')
        );
    $$;

CREATE OR REPLACE FUNCTION app_is_admin() RETURNS boolean
    LANGUAGE sql STABLE
    AS $$
        SELECT EXISTS (
            SELECT 1 FROM users
            WHERE id = auth.uid()
            AND role IN ('administrator', 'super_administrator')
        );
    $$;
"""

_ROLE_ESCALATION_TRIGGER = """
CREATE OR REPLACE FUNCTION app_prevent_role_self_escalation() RETURNS trigger AS $$
BEGIN
    -- current_user is the actual connected Postgres role. On a real Supabase
    -- project, direct client access (PostgREST) connects as `authenticated`
    -- or `anon`; the backend connects as its own dedicated role and is
    -- therefore exempt (role changes there already go through the RBAC-gated
    -- admin endpoint in app/api/routes/admin_users.py).
    IF NEW.role IS DISTINCT FROM OLD.role AND current_user IN ('authenticated', 'anon') THEN
        RAISE EXCEPTION 'Changing role via direct client access is not permitted.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_role_self_escalation
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION app_prevent_role_self_escalation();
"""

# (table, [policy statements])
_POLICIES: list[tuple[str, list[str]]] = [
    (
        "users",
        [
            "CREATE POLICY users_select_own_or_staff ON users "
            "FOR SELECT USING (id = auth.uid() OR app_is_staff())",
            "CREATE POLICY users_update_own_or_admin ON users "
            "FOR UPDATE USING (id = auth.uid() OR app_is_admin()) "
            "WITH CHECK (id = auth.uid() OR app_is_admin())",
        ],
    ),
    (
        "profiles",
        [
            "CREATE POLICY profiles_select_own_or_staff ON profiles "
            "FOR SELECT USING (user_id = auth.uid() OR app_is_staff())",
            "CREATE POLICY profiles_insert_own ON profiles "
            "FOR INSERT WITH CHECK (user_id = auth.uid())",
            "CREATE POLICY profiles_update_own_or_staff ON profiles "
            "FOR UPDATE USING (user_id = auth.uid() OR app_is_staff()) "
            "WITH CHECK (user_id = auth.uid() OR app_is_staff())",
            "CREATE POLICY profiles_delete_own_or_staff ON profiles "
            "FOR DELETE USING (user_id = auth.uid() OR app_is_staff())",
        ],
    ),
    (
        "user_preferences",
        [
            "CREATE POLICY user_preferences_all_own ON user_preferences "
            "FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid())",
        ],
    ),
    (
        "user_devices",
        [
            "CREATE POLICY user_devices_all_own ON user_devices "
            "FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid())",
        ],
    ),
    (
        "artist_profiles",
        [
            "CREATE POLICY artist_profiles_select_verified_own_or_staff ON artist_profiles "
            "FOR SELECT USING ("
            "verification_status = 'verified' OR user_id = auth.uid() OR app_is_staff()"
            ")",
            "CREATE POLICY artist_profiles_insert_own ON artist_profiles "
            "FOR INSERT WITH CHECK (user_id = auth.uid())",
            "CREATE POLICY artist_profiles_update_own_or_staff ON artist_profiles "
            "FOR UPDATE USING (user_id = auth.uid() OR app_is_staff()) "
            "WITH CHECK (user_id = auth.uid() OR app_is_staff())",
        ],
    ),
    (
        "designs",
        [
            "CREATE POLICY designs_select_published_own_or_staff ON designs "
            "FOR SELECT USING ("
            "status = 'published' "
            "OR app_is_staff() "
            "OR EXISTS ("
            "SELECT 1 FROM artist_profiles ap "
            "WHERE ap.id = designs.artist_profile_id AND ap.user_id = auth.uid()"
            ")"
            ")",
        ],
    ),
    (
        "bookings",
        [
            "CREATE POLICY bookings_select_participant_or_staff ON bookings "
            "FOR SELECT USING ("
            "customer_id = auth.uid() "
            "OR app_is_staff() "
            "OR EXISTS ("
            "SELECT 1 FROM artist_profiles ap "
            "WHERE ap.id = bookings.artist_profile_id AND ap.user_id = auth.uid()"
            ")"
            ")",
        ],
    ),
    (
        "messages",
        [
            "CREATE POLICY messages_select_conversation_member_or_staff ON messages "
            "FOR SELECT USING ("
            "app_is_staff() "
            "OR EXISTS ("
            "SELECT 1 FROM conversation_members cm "
            "WHERE cm.conversation_id = messages.conversation_id AND cm.user_id = auth.uid()"
            ")"
            ")",
        ],
    ),
    (
        "notifications",
        [
            "CREATE POLICY notifications_select_own ON notifications "
            "FOR SELECT USING (user_id = auth.uid())",
            "CREATE POLICY notifications_update_own ON notifications "
            "FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid())",
        ],
    ),
    (
        "payments",
        [
            "CREATE POLICY payments_select_own_or_staff ON payments "
            "FOR SELECT USING (payer_id = auth.uid() OR app_is_staff())",
        ],
    ),
]


def upgrade() -> None:
    op.execute(_AUTH_UID_SHIM)
    op.execute(_HELPER_FUNCTIONS)
    op.execute(_ROLE_ESCALATION_TRIGGER)

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

    op.execute("DROP TRIGGER IF EXISTS trg_prevent_role_self_escalation ON users")
    op.execute("DROP FUNCTION IF EXISTS app_prevent_role_self_escalation()")
    op.execute("DROP FUNCTION IF EXISTS app_is_admin()")
    op.execute("DROP FUNCTION IF EXISTS app_is_staff()")
    # Deliberately NOT dropping auth.uid(): on a real Supabase project this
    # function is managed by Supabase itself and must never be removed; on
    # local/CI Postgres, leaving the harmless shim in place is simpler and
    # safer than trying to distinguish "did this migration create it" after
    # the fact. See the module docstring.
