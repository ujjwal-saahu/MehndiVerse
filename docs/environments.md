# MehndiVerse — Environments (Phase 27)

Four environments, each with its own credentials and its own database/cache — none share state with another, so a bug or load test in one can't touch another's real data.

## Local

Developer machines. `docker-compose.yml` (postgres + redis + api); `apps/web`/`apps/admin` run via `npm run dev` outside Docker for fast iteration. Config: each app's `.env.example` (root, `apps/api`, `apps/web`, `apps/admin`) copied to a real `.env`/`.env.local`, gitignored. `ENVIRONMENT=development`. Supabase/Razorpay credentials are non-functional placeholders unless a developer has their own sandbox project — see docs/test-matrix.md#excluded-flows for what that means for local testing.

## Test

CI-only (`.github/workflows/ci.yml`) and `pytest`/`vitest` runs on a developer machine. Ephemeral Postgres/Redis (GitHub Actions service containers, or the same local Docker containers with a throwaway `_test`-suffixed database — see `tests/conftest.py`). `ENVIRONMENT=test`. `apps/api/.env.test.example` documents the shape. Every third-party call (Supabase, Razorpay, AI provider) is mocked (respx) — nothing in this environment ever reaches a real external service.

## Staging

A real, running deployment — the closest environment to production that isn't production. Own Supabase *project* (not just different keys against the same project — see `apps/api/.env.staging.example`), own Postgres/Redis, Razorpay in *test mode*. Deployed automatically from `main` after CI passes (`.github/workflows/deploy-staging.yml`) — see docs/deployment.md. Purpose: catch integration issues (real network calls, real streaming SSR, real CSP enforcement — see docs/test-matrix.md's CSP defect, found by a *browser*, not unit tests) before they reach production.

## Production

Real users, real money. Own Supabase project, own Postgres/Redis, Razorpay *live* mode. Deployed only by pushing a version tag (`.github/workflows/deploy-production.yml`), gated by required-reviewer manual approval — see docs/deployment.md#production-approval-gate. `apps/api/.env.production.example` documents the shape; every value is `__SECRET__` in that file on purpose (never fill it in — real values live only in the GitHub Environment's encrypted secrets).

## Secrets management

Every environment's real secrets live in a GitHub Environment (Settings -> Environments -> `staging`/`production`) or, for values CI itself needs regardless of environment (e.g. `GITHUB_TOKEN`, automatically provided), the platform's built-in secret store. Never in a committed file, never in a workflow's `env:` block as a literal value. GitHub Actions automatically redacts any log line containing a value that matches a registered secret — this is why every workflow reads credentials via `${{ secrets.* }}` and never `echo`s them (see docs/deployment.md#do-not-print-secrets-in-logs for the one thing this automatic redaction *doesn't* catch).

## Related documents

- [docs/deployment.md](deployment.md)
- [docs/rollback.md](rollback.md)
- [docs/security-review.md#secret-handling](security-review.md#secret-handling)
