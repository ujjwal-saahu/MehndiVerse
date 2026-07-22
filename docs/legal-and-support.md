# MehndiVerse — Legal, Privacy, and Customer-Support Foundation (Phase 29)

Resolves the open question flagged in [security-baseline.md §9](security-baseline.md) ("data retention practices... flagged as an open question, not resolved in Phase 0") and gives every legal/support surface referenced from `apps/web` a real, working page and backend record.

## Legal-review status

**Every page under `/legal/*` renders a "Draft — pending qualified legal review" banner** (`apps/web/src/components/legal/legal-review-notice.tsx`) and must not be represented as legally reviewed or compliant until qualified counsel signs off — removing the banner is that sign-off, not a copy edit. This applies to: Privacy Policy, Terms of Service, Community Guidelines, Artist Terms, Cancellation Policy, Refund Policy. The AI-Content Disclosure and Cookie Policy pages are factual/product disclosures describing what the system actually does today (verified against `docs/ai-foundation.md`, `docs/ai-design-assistant.md`, `docs/analytics-and-recommendations.md`) rather than legal-drafting placeholders, but should still be reviewed before launch.

The Cancellation Policy and Refund Policy pages explicitly flag that **no automated fee schedule or eligibility window exists in the code** — every cancellation/refund involving money is reviewed individually by staff today (see `docs/booking-lifecycle.md`, `docs/performance-and-reliability.md#payment-reconciliation-test`). Do not add a specific percentage/timeframe to those pages without a matching business decision and, ideally, matching enforcement logic — an unenforced promise on a legal page is worse than no promise.

## Data-retention categories

| Category | Retained | Why |
|---|---|---|
| Account/profile (email, phone, display name, bio) | Until account deletion, then anonymized (see below) | Core account operation |
| Bookings, booking status history | Indefinitely, even after the customer's account is anonymized | `Booking.customer_id` uses `ON DELETE RESTRICT`-equivalent (never hard-deleted); an artist's own booking/earnings history must stay intact |
| Payments, payouts, refunds (`payments`, `payouts`, `refunds`) | Indefinitely | Financial/tax record-keeping — never deleted or anonymized by account deletion (see `app/services/account_deletion.py`, which touches only `User`/`Profile`/`UserDevice`) |
| Audit logs (`audit_logs`) | Indefinitely | Immutable by design (`app/db/models/system.py::AuditLog` docstring: "no updated_at, no soft delete, ever") |
| Consent records (`consent_records`) | Indefinitely | Evidence of what was consented to and when — deleting it would defeat its own purpose |
| Reviews, messages, comments | Retained after the author's account is anonymized (soft-deleted only) | So the *other* party's booking/review history isn't destroyed by someone else's account deletion — same reasoning `account_deletion.py`'s docstring already gives |
| Verification documents (artist onboarding) | Until the artist's account is deleted; signed URLs expire independently | Private Supabase Storage bucket, never public |
| Analytics events (`analytics_events`) | Indefinitely, but never attributable to a user who hasn't set `analytics_consent = True` | See `docs/analytics-and-recommendations.md#provide-analytics-consent-where-legally-required` |
| Support requests (`support_requests`) | Indefinitely | Operational history; `user_id` is nulled if the account is later deleted (`ON DELETE SET NULL`) |
| Data-export request log (`data_export_requests`) | Indefinitely (metadata only — see below) | Audit trail of when an export was served; the export payload itself is never stored |

## Third-party processors

| Processor | Purpose | Data shared |
|---|---|---|
| Supabase (Auth) | Authentication, session tokens | Email, password hash (never touches our DB directly) |
| Supabase (Postgres) | Primary database | All application data |
| Supabase (Storage) | File storage (avatars, portfolio images, verification documents, previews) | Uploaded files, behind signed URLs |
| Razorpay | Payment processing | Payment amount, booking reference — **never** card/bank details, which Razorpay collects directly |
| Sentry (if `SENTRY_DSN` is configured — see `docs/observability.md`) | Error tracking | Request metadata, with `Authorization`/`Cookie`/`X-Metrics-Token` headers redacted (`app/core/error_tracking.py`) |

No advertising or cross-site-tracking third party is used anywhere in this codebase today.

## Consent records

`app/db/models/support.py::ConsentRecord` — an append-only ledger (`ConsentType`: `terms_of_service`, `privacy_policy`, `cookies_analytics`), never edited or deleted, `user_id` uses `ON DELETE RESTRICT` (in practice never exercised, since account deletion anonymizes the `User` row rather than deleting it).

- **Terms of Service / Privacy Policy** — recorded automatically inside `POST /auth/register` (`app/api/routes/auth.py::register`) the moment an account is created. `RegisterRequest.terms_accepted` must be `true` (422 otherwise) — the web register form (`apps/web/src/app/(auth)/register/page.tsx`) requires the checkbox before it will submit. This is the one point every account passes through, so it's the single place this consent is captured — not left to a client-side follow-up call that could be skipped.
- **Cookies/analytics** — the cookie-consent banner (`apps/web/src/components/legal/cookie-consent-banner.tsx`) sets `UserPreference.analytics_consent` via the existing `PATCH /users/me/preferences` endpoint (Phase 22) — the same flag `record_event()` already checks before attaching a user's identity to an analytics event. A signed-out visitor's choice is saved to `localStorage` only (there's no identity yet to attach a server-side record to); it takes effect for real once they sign in and the same preference exists on their account.
- `GET`/`POST /legal/consent` (`app/api/routes/legal.py`) is a general-purpose consent ledger available for any future consent type — tested (`tests/legal/test_consent.py`) but **not currently called from either web app**, since the two consent types that exist today are each handled by a more specific, better-integrated mechanism above. Wiring a "view your consent history" page to `GET /legal/consent` is a reasonable, low-cost follow-up, not done this phase to avoid an unused UI surface.

## Account deletion and financial/audit-record retention

Unchanged from the existing `app/services/account_deletion.py` (pre-dates this phase) — this phase's job was to *document* it, not rebuild it. `POST /auth/account/deletion-request` flags the account; after a grace period (`account_deletion_grace_period_days`), `process_pending_deletions()` anonymizes `User`/`Profile`, deletes `UserDevice` rows, and writes one `account.deletion_finalized` audit-log entry. It deliberately:

- **Never touches** `payments`, `payouts`, `refunds`, or `audit_logs` — see the [data-retention table](#data-retention-categories) above for why.
- **Never cascade-deletes** bookings, reviews, or messages — the other party's history must survive.
- **Never calls Supabase's Admin API** to delete the underlying `auth.users` row — a documented gap (`account_deletion.py`'s own docstring), since that needs a service-role-authenticated GoTrue Admin API integration this codebase doesn't have yet.

## Data-export request

`GET /account/data-export` (`app/api/routes/account_export.py`, `app/services/legal.py::build_account_data_export`) — generates a JSON export of the caller's own profile, bookings, payments, reviews, consent records, and support requests **on demand**, and returns it directly; nothing is emailed or stored server-side (a `DataExportRequest` audit row records only that an export happened, not its contents — storing a second copy of a full personal-data export would itself be a new data-retention liability). Surfaced at `/account/data-export` (web) via a "Download my data" button that saves the response as a `.json` file, linked from the main `/account` page.

## Report a problem and contact support

Both "Report a problem" and "Contact support" post to the same `POST /support/requests` (`app/api/routes/support.py`, `app/db/models/support.py::SupportRequest`) — a free-text `category`/`subject`/`message` triaged by staff, rate-limited (`support_request_rate_limit`, default `5/minute`) the same way `app/api/routes/reports.py` is. Usable signed-out (`get_current_user_optional` — a *missing* token is treated as a guest, but a *present-and-invalid* token still raises `401`, since silently downgrading a bad token to "guest" would hide a real bug or attack) — a guest identifies themselves only by the `contact_email` they type in.

This is distinct from `app/db/models/moderation.py::Report`, which reports a specific design/comment/message/user for a policy violation and enters the existing moderation queue — the Community Guidelines page links to that "Report" action instead for that case.

## Cookie and analytics consent

See [Consent records](#consent-records) above and `apps/web/src/app/(marketing)/legal/cookies/page.tsx`. No cookie beyond the strictly-necessary session cookie and the analytics-consent preference exists in this codebase today — the banner is a foundation for the one real preference that exists (`analytics_consent`), not a rewrite of the session/CSRF cookies documented in `docs/security-review.md#csrf`.

## What this phase deliberately does not do

- **No full translation of legal document bodies.** Translating a legal document's actual text into Hindi/Urdu/Arabic before qualified legal review has approved the *English* source would mean translating text that may still change — the surrounding page chrome uses the existing i18n system where practical (register form's consent checkbox, footer links), but the legal documents' own body text is English-only until reviewed.
- **No re-prompt-on-version-bump flow.** `app/core/legal.py`'s version constants exist so a future change can detect "this user consented to an older version," but nothing re-prompts a user yet if `CURRENT_TERMS_VERSION` changes.
- **No admin UI for browsing `support_requests` or `consent_records`.** Both are queryable via the database/a future admin-dashboard phase; this phase built the customer-facing capture path, not a staff triage view.
- **No automated cancellation-fee or refund-eligibility engine** — see the [legal-review status](#legal-review-status) section above.

## Related documents

- `docs/security-baseline.md` §9 — the open question this phase resolves.
- `docs/booking-lifecycle.md`, `docs/performance-and-reliability.md` — cancellation/refund/reconciliation mechanics referenced by the policy pages.
- `docs/analytics-and-recommendations.md` — `analytics_consent`, the mechanism the cookie banner drives.
- `docs/ai-foundation.md`, `docs/ai-design-assistant.md` — source material for the AI-content disclosure page.
- `docs/observability.md` — Sentry/logging redaction, referenced in the third-party-processors table.
