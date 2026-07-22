# MehndiVerse — Rollback Procedures (Phase 27)

Companion to [docs/deployment.md](deployment.md) and [docs/incident-response.md](incident-response.md) (that document's playbooks are for security incidents; this one is for "the new deploy itself is broken").

## Application rollback (api / web / admin)

Every image is tagged with both a moving tag (`staging`, `production`) and an immutable one (`staging-<sha>`, `v<version>`) — see docs/deployment.md's build/promote steps. Rolling back never means "revert the commit and redeploy" (slow: a full CI + rebuild cycle) — it means re-pointing the running deployment at the last-known-good immutable tag, which already exists in the registry.

### Staging rollback

1. Identify the last-good SHA (the previous `deploy-staging.yml` run that passed its `smoke-test` job).
2. Re-run the `deploy` job's rollout step against `ghcr.io/<repo>/{api,web,admin}:staging-<last-good-sha>` instead of the current tag (manual `workflow_dispatch` with that tag, once the placeholder `deploy` step is filled in for a real hosting platform).
3. Re-run `smoke-test` to confirm.

### Production rollback

1. Identify the last-good version tag (the previous `deploy-production.yml` run that passed its `smoke-test` job — check GitHub Releases, created by `create-release`).
2. Re-run the rollout step against `ghcr.io/<repo>/{api,web,admin}:v<last-good-version>`.
3. Re-run the migrate job's logic in reverse **only if safe** — see [Database migration rollback limitations](#database-migration-rollback-limitations) below; most rollbacks should roll back the *application* without touching the schema at all (additive migrations are forward-compatible with the old app version — see that section).
4. Re-run `smoke-test`.
5. File a post-mortem per docs/incident-response.md#5-post-mortem regardless of severity — a production rollback is itself worth a short retro even when it wasn't a security incident.

## Database migration rollback limitations

`alembic downgrade` is **not** a general-purpose undo button, even though every migration has a `downgrade()` function and CI's `migrations` job (docs/deployment.md#ci) verifies the *entire chain* downgrades and re-upgrades cleanly. That check runs against a **throwaway, empty-of-real-data** database — it proves the SQL is syntactically reversible, not that reversing it is safe once real rows depend on the schema it's undoing. Concretely:

- **Destructive downgrades lose data, silently.** A migration that drops a column (or a table) has a `downgrade()` that re-creates it *empty* — any data written to that column after the upgrade is gone the moment `downgrade` runs, with no warning. CI's throwaway database never has this data, so the check can't catch it.
- **A downgrade run after the new application code has already written new-shape data will corrupt that data**, not just lose it — e.g. a migration that changes a column's type or constraint, downgraded after rows already exist in the new shape, can leave rows the old schema can't represent correctly.
- **RLS policies and triggers** (see docs/security-review.md#row-level-security) are dropped and recreated by their own migrations' `downgrade()` — a downgrade that removes a policy briefly leaves that table without its RLS backstop until the app-level authorization (the primary layer) is confirmed still correct for the older schema.

**The safe default: never run `alembic downgrade` against staging or production.** Roll back the *application* to the previous image instead (see above) — every migration in this codebase is written additively (new nullable columns, new tables, new indexes) specifically so the *previous* application version keeps working unmodified against the *new* schema (it just doesn't know about the new columns/tables yet). This is why [Production rollback](#production-rollback) step 3 says "only if safe" — the deliberate default is "don't," and a real downgrade is a case-by-case judgment call requiring someone to manually verify no destructive step in the chain being undone has real data behind it, not a routine part of the rollback procedure.

If a schema change genuinely must be undone (e.g. it's actively breaking production and rolling back the app alone doesn't fix it): take a database backup first (docs/security-review.md#backup-access-controls; `scripts/backup_restore_test.sh` documents and verifies the mechanics), then downgrade one migration at a time, verifying data integrity after each step — never `alembic downgrade base` or a multi-step jump against a database with real data, regardless of what CI's full-chain check demonstrated against an empty one.

## Related documents

- [docs/deployment.md](deployment.md)
- [docs/incident-response.md](incident-response.md)
- [docs/migration-guidelines.md](migration-guidelines.md)
