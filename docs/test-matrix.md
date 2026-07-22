# MehndiVerse — Test Matrix (Phase 26)

Coverage audit + gap-filling for `apps/api`, `apps/web`, `apps/admin`, `apps/mobile`, plus new end-to-end journeys under `/e2e`. Numbers below are from this phase's actual runs, not estimates.

## Current state

| Surface | Tests | Result |
|---|---|---|
| `apps/api` | 1068 passed, 1 skipped | `pytest --cov=app`: **93%** line coverage (was 92% before this phase's additions) |
| `apps/web` | 351 passed | vitest |
| `apps/admin` | 45 passed | vitest |
| `apps/mobile` | 34 test files | **not run this phase** — no `flutter`/`dart` binary in this environment (see [Required manual tests](#required-manual-tests)) |
| `/e2e` | 10 passed | 7 from Phase 26 + 3 new in Phase 30 (`resilience-and-accessibility.spec.ts`: expired session, RTL, throttled network) — see [docs/staging-deployment.md](staging-deployment.md) |

## Covered flows

### Backend (`apps/api`)
- **Unit tests**: service-layer logic across `app/services/*` (booking state machine, subscriptions, payments, AI, moderation, scheduling) — see per-module test dirs under `tests/`.
- **API integration tests**: route-level tests for every router in `app/api/routes/` (147 test files total).
- **Authorization tests**: `require_roles()`/ownership checks exercised per-endpoint throughout; dedicated cross-cutting cases in `tests/profile/test_privacy_authorization.py`.
- **Database tests**: `tests/db/` — schema constraints, cascade/FK behavior, booking-transition validity (`test_booking_transitions.py`).
- **Booking state-machine tests**: `tests/db/test_booking_transitions.py`, `tests/booking/test_draft_and_submission.py`, `test_quotes_and_confirmation.py`, `test_cancellation_and_reschedule.py`.
- **Booking concurrency tests**: `tests/booking/test_confirmation_concurrency.py` (concurrent quote-confirmation race).
- **Payment-webhook tests**: `tests/payments/test_webhooks.py` (signature verification, idempotency), `tests/subscriptions/test_webhook_settlement.py`.
- **Subscription tests**: `tests/subscriptions/*` — checkout, entitlements/quotas, cancellation/expiration, coupons; **new this phase**: `test_billing_and_status_history.py` (both endpoints had zero coverage before).
- **Moderation tests**: `tests/community/test_admin_moderation.py`, `test_reports.py`; **new this phase**: unknown-status-filter validation case.
- **AI-provider mock tests**: `tests/ai/*` — local provider, job queue, sandbox test against a mocked provider; **new this phase**: `test_tag_suggestion_and_generation_routes.py` (tag-suggestion list/resolve, embedding/moderation-check request routes — all previously untested at the HTTP layer).
- **New this phase**: `tests/booking/test_attachment_upload.py` — `POST /bookings/{id}/attachments` had zero coverage (a full endpoint, including an authorization boundary between customer/artist parties).

### Web / Admin
- **Component tests**: extensive existing vitest + Testing Library coverage across `apps/web/src/components/*` and `apps/admin/src/components/*`.
- **Form tests**: react-hook-form + zod schemas covered per form component (login, register, edit-profile, settings, admin moderation actions).
- **Protected-route tests**: `apps/web/src/middleware.test.ts` (22 cases), `apps/admin/src/middleware.test.ts` (7 cases, updated this phase for the CSP change).
- **Permission tests**: admin components gate on role via `requireStaffUser()`/`requireEditStaffUser()`/`requireSuperAdminUser()` (`apps/admin/src/lib/current-staff-user.ts`) — exercised by admin page-level tests and now by `/e2e`.
- **End-to-end customer journey**: `/e2e/specs/customer-journey.spec.ts` — signed-out browsing/login redirect, authenticated account + discover page access.
- **End-to-end artist journey**: `/e2e/specs/artist-journey.spec.ts` — verified artist reaches booking inbox; unverified artist redirected to onboarding.
- **End-to-end admin moderation journey**: `/e2e/specs/admin-moderation-journey.spec.ts` — non-staff redirected, moderator reaches reports queue, signed-out redirected to admin login.

## Excluded flows

- **Real Supabase Auth UI flows** (typing email/password into the login form and having it actually authenticate) — this environment only has placeholder Supabase credentials (`SUPABASE_URL=https://placeholder.supabase.co`), so there is no real project to authenticate against. `/e2e` instead mints JWTs locally with the same secret the backend verifies against (`e2e/helpers/auth.ts`) and injects them as session cookies — this exercises real middleware/page/backend authorization code, just not the Supabase Auth API call itself.
- **Real Razorpay checkout** — sandbox/test-mode credentials are also placeholders here; payment-provider integration is covered by mocked-provider tests (`tests/payments/`), not a real checkout flow.
- **Flutter test execution** — see [Required manual tests](#required-manual-tests).
- **Full RTL/contrast/touch-target visual audit** (carried over from Phase 24) — still not done; unrelated to this phase's scope.
- **Golden tests** — none exist for `apps/mobile`; not added this phase (no toolchain to generate/verify golden baselines against — a golden test committed without ever running would be worse than no golden test).

## Required manual tests

- **Run the full Flutter test suite** (`cd apps/mobile && flutter test`) — this environment has no `flutter`/`dart` binary at all (`which flutter`/`which dart` both fail), so none of the 34 existing test files were executed this phase, and no new Flutter tests were added (a Dart change nobody can compile-check is worse than not making it — same reasoning applied in Phase 25). Specifically missing, to add once a toolchain is available:
  - **Booking integration tests** — `lib/features/bookings/` has real screens (`my_bookings_screen.dart`, `booking_detail_screen.dart`) but no corresponding test file exists for either; the only "booking" mentions in `test/` are an incidental `isAcceptingBookings` fixture flag. This is the single biggest mobile gap.
  - **Payment-state tests** — no dedicated payment-flow test file; the only "payment" mention in `test/` is a single UI-string assertion (`'Your last payment failed'`) inside `subscription_status_screen_test.dart`, not a payment-state integration test.
  - **Dedicated Riverpod provider tests** beyond `auth_controller_test.dart` — most providers are only exercised indirectly through screen widget tests.
  - **Golden tests** for the screens this project would consider "important" (home, gallery detail, booking inbox) — requires generating and committing baseline images with a real Flutter SDK, then reviewing them for actual visual correctness, neither of which is possible without one.
- **Real device / real network conditions** — none of this phase's work (or prior phases') has been tested on physical hardware or a throttled/offline network; the Phase 25 "low-network behavior" work is code-reviewed, not device-tested.
- **Accessibility**: screen-reader walkthroughs, RTL visual review — flagged as manual since Phase 24, still outstanding.

## Required provider sandbox tests

Once real (non-placeholder) credentials exist for a given provider, these need to run against the actual sandbox — not just the mocked-provider unit/integration tests already in place:

- **Supabase Auth**: real sign-up (with real email delivery/verification), password reset email delivery, and session refresh against an actual Supabase project.
- **Supabase Storage**: real upload/signed-URL retrieval against a real bucket (this phase's mocked tests only verify the HTTP calls our code makes are shaped correctly, not that a real bucket accepts them).
- **Razorpay**: a real sandbox checkout end-to-end (order creation → hosted checkout UI → webhook delivery → reconciliation), and a real refund. `tests/payments/test_webhooks.py` verifies signature handling against a hand-crafted payload, not Razorpay's actual webhook delivery format/timing/retries.
- **Firebase Cloud Messaging** (`apps/mobile`): a real push notification delivered to a real or emulated device — `app/integrations/push_notifications.py`'s tests mock the FCM HTTP call.

## Defects fixed

**Severity: high.** Phase 24's Content-Security-Policy (`script-src 'self'`, no nonce, set as a static header in each app's `next.config.ts`) silently blocked Next.js's own required inline hydration script in any CSP-enforcing browser. Effect: every page using a Suspense boundary (i.e. most authenticated pages doing a server-side fetch) rendered its loading skeleton and **never resolved to real content** — invisible to `curl`-based verification (no JS execution, no CSP enforcement) and to the unit/component test suites (jsdom doesn't enforce CSP either), which is exactly why it survived Phase 24's verification undetected. Found by the first real-browser E2E test in this project (Playwright, headless Chromium, CSP-enforcing). Console evidence: `Invariant: Expected a request ID to be defined for the document via self.__next_r. This is a bug in Next.js` plus repeated CSP violation reports for the inline hydration script.

Fix: moved CSP from `next.config.ts` (static) to `middleware.ts` (per-request), using Next.js's documented nonce pattern — `script-src 'self' 'nonce-{random}'`, propagated via an `x-nonce` request header and the response's `Content-Security-Policy` header. Applied identically to `apps/web` and `apps/admin` (same defect, same fix). Dev mode also needs `'unsafe-eval'` (React DevTools' stack-reconstruction, never used in production) — gated by `NODE_ENV`, mirroring how `app/core/security_headers.py` already gates HSTS.

Verified: all 7 `/e2e` specs pass against production builds' dev-mode servers; `apps/web`/`apps/admin` unit/component suites (351 + 45) still pass; both apps' production builds succeed.

## Related documents

- [docs/security-review.md#security-headers](security-review.md#security-headers) — original CSP addition this phase's fix supersedes.
- [docs/performance-and-reliability.md](performance-and-reliability.md) — the Phase 25 work this phase's coverage audit builds on.
