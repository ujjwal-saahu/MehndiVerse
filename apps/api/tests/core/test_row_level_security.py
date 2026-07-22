"""Confirms the Phase 24 RLS-extension migration
(58e26672bf4e_extend_row_level_security_coverage) actually left the
database in the state it claims to — see docs/security-review.md#row-
level-security. The application's own DB role bypasses RLS (see that
migration's docstring), so nothing in the rest of the test suite would
otherwise notice a policy silently failing to apply or being dropped by a
later migration."""

from sqlalchemy import text
from sqlalchemy.orm import Session

_EXPECTED_TABLES = {
    "conversations",
    "conversation_members",
    "reviews",
    "collections",
    "subscriptions",
    "reports",
    "preview_projects",
    "ai_generations",
    "ai_design_requests",
    "audit_logs",
}


def test_row_level_security_is_enabled_on_every_extended_table(db_session: Session) -> None:
    rows = db_session.execute(
        text(
            "SELECT tablename, rowsecurity FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = ANY(:tables)"
        ),
        {"tables": list(_EXPECTED_TABLES)},
    ).all()
    found = {row.tablename: row.rowsecurity for row in rows}

    assert set(found) == _EXPECTED_TABLES
    assert all(found.values()), f"RLS disabled on: {[t for t, on in found.items() if not on]}"


def test_audit_logs_has_no_client_write_policy(db_session: Session) -> None:
    """audit_logs must stay staff-read-only with no INSERT/UPDATE/DELETE
    policy for any role — see the migration's rationale."""
    rows = db_session.execute(
        text("SELECT cmd FROM pg_policies WHERE schemaname = 'public' AND tablename = 'audit_logs'")
    ).all()
    commands = {row.cmd for row in rows}
    assert commands == {"SELECT"}


def test_every_extended_table_has_at_least_one_policy(db_session: Session) -> None:
    rows = db_session.execute(
        text(
            "SELECT tablename, count(*) AS n FROM pg_policies "
            "WHERE schemaname = 'public' AND tablename = ANY(:tables) "
            "GROUP BY tablename"
        ),
        {"tables": list(_EXPECTED_TABLES)},
    ).all()
    counts = {row.tablename: row.n for row in rows}
    assert set(counts) == _EXPECTED_TABLES
    assert all(n > 0 for n in counts.values())
