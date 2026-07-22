# MehndiVerse — Staging Deployment & QA (Phase 30)

## What "staging" means in this environment

This sandbox has no real cloud project, domain, or provider credentials (Supabase/Razorpay/FCM are all placeholders — same constraint documented since Phase 0, see `docs/test-matrix.md#excluded-flows`). Phase 27's `deploy-staging.yml` GitHub Actions workflow (real target: a GitHub Environment + a live host) cannot be triggered from here for the same reason `docker build`s in prior phases couldn't be pushed to a registry.

What **was** done, as the closest verifiable substitute:

1. **Built the actual staging artifacts** — `docker build` for all three Dockerfiles (`apps/api`, `apps/web`, `apps/admin`), the same images `deploy-staging.yml` would build and push. All three succeeded.
2. **Ran the built application**, not a mock — `apps/api` via `uvicorn` (`ENVIRONMENT=staging`) against the project's real local Postgres/Redis; `apps/web` and `apps/admin` via `next build && next start` (production mode, not dev), each pointed at the live api via `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` (`.env.local`, gitignored).
3. Confirmed all three serve traffic: `GET /health` → `{"status":"ok","database":"ok","cache":"ok"}`, `GET /health/live` → `{"status":"ok"}`, `apps/web` `/` → 200, `apps/admin` `/login` → 200.
4. Ran every automated test suite fresh against this live stack (not cached results from an earlier phase).

## Results

| Suite | Result |
|---|---|
| `docker build` — api / web / admin | All 3 succeeded |
| `apps/api` pytest | 1102 passed, 1 skipped, 1 deselected (known flaky test) |
| `apps/web` vitest | 362 passed |
| `apps/admin` vitest | 45 passed |
| `/e2e` Playwright, against the live stack above | **10 passed** (7 existing + 3 new — see below) |

## New this phase: `e2e/specs/resilience-and-accessibility.spec.ts`

Closes part of the "Real device / real network conditions" and RTL gaps `docs/test-matrix.md` had flagged as manual-only:

- **Expired session** — a validly-signed JWT with `exp` in the past (`e2e/helpers/auth.ts::signExpiredAccessToken`) correctly redirects `/account` to `/login` instead of showing stale/broken data.
- **RTL layout** — setting the locale cookie to `ar` renders `<html dir="rtl">`.
- **Slow network** — every request delayed 200ms (`page.route`); `/discover` still reaches a correct loaded state within budget rather than hanging.

## Full QA checklist — what each item is actually verified by

Every flow Phase 30 asked to verify already has passing automated coverage from prior phases, re-run fresh this phase against the live stack above (not re-listed file-by-file here — see `docs/test-matrix.md` for the exhaustive per-flow file map): customer registration/login/profile editing, design discovery/search/filters/likes/collections, artist onboarding/verification/portfolio/services/availability, booking request/quote/confirmation, messaging, sandbox payment/refund (mocked-provider — see `docs/test-matrix.md#excluded-flows` for why not a real Razorpay sandbox), review, report, admin moderation, subscription sandbox, virtual preview, AI assistant sandbox, push/email notifications (foundation-level — logs the attempt, no real provider configured, same as every prior phase).

**Not executable in this sandbox** (unchanged from Phase 26, re-confirmed, not re-litigated): Android/iOS/mobile-browser testing (no Flutter toolchain, no device farm, no physical hardware), a full RTL/contrast/touch-target visual audit (this phase adds one structural `dir="rtl"` check, not a full visual review), a real provider sandbox pass (Supabase/Razorpay/FCM), the Flutter test suite (34 files, still no `flutter`/`dart` binary).

## Bug list

See `docs/bug-list-phase30.md`.

## Related documents

- `docs/test-matrix.md` — full per-flow coverage map, excluded flows, required manual tests.
- `docs/deployment.md`, `docs/environments.md` — the real staging/production pipeline this phase's local run stands in for.
- `docs/bug-list-phase30.md` — this phase's classified findings.
