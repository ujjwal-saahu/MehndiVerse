# MehndiVerse — Deployment (Phase 27)

See [docs/environments.md](environments.md) for what each environment is. This document is how code moves between them.

## CI (`.github/workflows/ci.yml`)

Runs on every push to `main` and every pull request. Jobs: `backend` (ruff format/lint, mypy, pytest), `web`/`admin` (eslint, tsc, vitest, **`next build`**), `mobile` (flutter analyze, flutter test), `migrations` (full upgrade → downgrade base → upgrade round-trip against a throwaway database — see [Database migration rollback limitations](rollback.md#database-migration-rollback-limitations) for what this does and doesn't prove), `docker-compose` (config validation), `secret-scan` (gitleaks), `dependency-scan` (pip-audit, npm audit). Workflow-level `permissions: contents: read` — no job can write to the repo unless it explicitly elevates (only `create-release` in the production workflow does).

## Prevent deployment if tests fail

`deploy-staging.yml` triggers on `workflow_run` of the `CI` workflow and its `gate` job checks `github.event.workflow_run.conclusion == 'success'` — every later job `needs: gate` (directly or transitively), so a red CI run never reaches build-and-push, migrate, or deploy. `deploy-production.yml` triggers on a version tag rather than CI completion directly, but [Versioning](#versioning) below only tags commits that already went through a green `main` build, and `promote-images` re-tags the *already-staging-deployed* image rather than rebuilding — production can only ever run bytes that already passed CI and staging.

## Staging deployment (`deploy-staging.yml`)

1. `gate` — confirms CI passed.
2. `build-and-push-images` — builds `apps/api/Dockerfile`, `apps/web/Dockerfile`, `apps/admin/Dockerfile` and pushes to GHCR, tagged `staging` and `staging-<sha>`.
3. `migrate` — `alembic upgrade head` against the staging database.
4. `deploy` — rolls the new images out. **Placeholder**: no hosting platform has been chosen for this project yet (no Vercel/Railway/Fly/AWS decision exists in `docs/` — grepped for it, found none), so this step is documented rather than implemented; everything before it (build, push, migrate) is real and runs against real staging secrets today.
5. `smoke-test` — `curl`s `/health` and fails the run (with a pointer to [docs/rollback.md](rollback.md#staging-rollback)) if it doesn't respond.
6. `background-workers` — restart signal for the scheduled jobs (see below); also a placeholder for the same reason as `deploy`.

## Production deployment (`deploy-production.yml`)

Triggered only by pushing a `v*.*.*` tag — never by a push to `main` directly, so cutting a release is always a deliberate, separate action. `resolve-version` → `promote-images` (re-tags the staging image that SHA already produced, doesn't rebuild — see [Prevent deployment if tests fail](#prevent-deployment-if-tests-fail)) → `migrate` → `deploy` (placeholder, same reason as staging) → `smoke-test` → `create-release` (a GitHub Release with generated notes).

### Production approval gate

Every job in `deploy-production.yml` sets `environment: production`. This activates GitHub's environment-protection gate *only once the repo setting exists*: **Settings → Environments → production → Required reviewers** — add at least one person/team there. This is a one-time manual repo-configuration step; no workflow YAML can express it (GitHub deliberately keeps this out of version control, since a compromised workflow file must not be able to grant itself deploy approval). Until that setting is turned on, this workflow will run production deploys with **no** human gate — turning it on is a hard prerequisite, not optional polish.

### Background workers

No message queue exists in this codebase (each `app/cli/process_*.py` module's own docstring says so). `.github/workflows/scheduled-jobs.yml` *is* the worker scheduler: cron-triggered, runs `process_ai_jobs` (every 5 min), `reconcile_payments` (hourly), `process_subscriptions`/`process_account_deletions` (daily) against the `production` GitHub Environment's secrets. Every one of these jobs is idempotent by design (see docs/performance-and-reliability.md#idempotent-tasks) — an overlapping or skipped run is never destructive, which is what makes a simple cron schedule (rather than a real queue with locking) an acceptable foundation.

## Secrets management

Every deploy workflow reads credentials exclusively via `${{ secrets.STAGING_* }}` / `${{ secrets.PRODUCTION_* }}`, sourced from that GitHub Environment's encrypted secret store (Settings → Environments → staging/production → Environment secrets). Nothing here is a repository-level secret shared across environments — a staging credential physically cannot be used against production and vice versa, since the workflow only ever requests the secret scoped to the environment its job declares.

## Do not print secrets in logs

GitHub Actions automatically redacts (`***`) any log line containing the exact string value of a registered secret. This is why every workflow step that touches a credential passes it through `env:` and references `$VARIABLE_NAME` in the shell rather than interpolating `${{ secrets.X }}` directly into a `run:` command string — the latter is a known way to accidentally leak a *transformed* version of a secret (e.g. base64-encoded, or with whitespace trimmed) that no longer matches the registered value byte-for-byte, defeating the redaction. None of this repo's workflows `echo` a secret directly, and none pass a secret as a CLI argument (visible in process listings) — always via environment variable.

## Require protected production branches

Required (one-time) repo settings, since GitHub branch protection isn't expressible in a workflow file:

- **Settings → Branches → Add rule → `main`**: "Require a pull request before merging", "Require review from Code Owners" (pairs with [`CODEOWNERS`](../CODEOWNERS)), "Require status checks to pass before merging" (select every `ci.yml` job), "Do not allow bypassing the above settings" (applies it to admins too, not just contributors).
- No one pushes to `main` directly, and no PR merges with a red CI run or without review — this is what makes "CI passed on main" (the precondition [Prevent deployment if tests fail](#prevent-deployment-if-tests-fail) relies on) a trustworthy signal rather than something a single contributor could route around.

## Versioning

Semantic versioning (`vMAJOR.MINOR.PATCH`), root [`VERSION`](../VERSION) file as the single source of truth for the *release* version (independent of each subproject's own `package.json`/`pyproject.toml` version field, which aren't required to match it). A release is cut by: bump `VERSION`, merge to `main` via the normal PR process, then `git tag vX.Y.Z && git push origin vX.Y.Z` — that tag push is what triggers `deploy-production.yml`. Mobile (`apps/mobile/pubspec.yaml`) keeps its own independent `version: X.Y.Z+build` — Flutter's own app-store versioning convention, unrelated to this scheme (app-store releases are a separate, manual process not covered by this phase).

## Related documents

- [docs/environments.md](environments.md)
- [docs/rollback.md](rollback.md)
- [docs/incident-response.md](incident-response.md)
