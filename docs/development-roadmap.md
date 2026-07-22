# MehndiVerse — Development Roadmap

Status: Draft (Phase 0)
Last updated: 2026-07-14

MehndiVerse is built incrementally, one explicitly-scoped phase at a time — no phase begins until the previous one is delivered and verified. This document sequences work; it does not commit to calendar dates. Phase numbers are stable identifiers; phase content may be refined as earlier phases surface new information, but changes should be reflected here so this stays the source of truth for "what phase are we on."

## Sequencing principles

* Each phase produces something independently verifiable (builds, runs, or documents cleanly) before the next starts.
* Foundational/shared infrastructure (auth, data models, API scaffolding) comes before feature-specific work that depends on it.
* MVP features (per [feature-scope.md](feature-scope.md)) are fully sequenced before any Post-MVP or Future feature is scheduled.
* Admin tooling for a capability lands close to the customer/artist-facing capability it governs (e.g., artist verification tooling ships alongside artist onboarding), not deferred to the very end.
* Security, testing, and observability are not a separate late phase — they are a standing requirement within every phase per [security-baseline.md](security-baseline.md).

## Phases

### Phase 0 — Product planning and repository audit (this phase)
Documentation only: product requirements, roles/permissions, feature scope, architecture, roadmap, security baseline, and the technology-stack decision record. No application code.

### Phase 1 — Foundation and repository scaffolding
Establish the monorepo/multi-app structure, base tooling (linting, formatting, CI skeleton), and empty-but-runnable shells for the FastAPI backend, Next.js customer app, Next.js admin app, and Flutter app. Supabase project provisioning and environment variable conventions (`.env.example` files). No business features yet.

### Phase 2 — Auth and core data model
Supabase Authentication integration across all three clients. Core PostgreSQL schema for users and roles (Guest/Customer/Premium Customer/Artist/Verified Artist/Moderator/Administrator/Super Administrator) via SQLAlchemy + Alembic migrations. Baseline RLS policies. Server-side authorization middleware in FastAPI.

### Phase 3 — Design catalog
Design data model, category/taxonomy management (admin), browse/search/filter endpoints and UI (mobile + customer web), design detail views, like/save and basic collections.

### Phase 4 — Artist profiles and verification
Artist registration and profile management, portfolio upload (Supabase Storage), verification document submission, admin verification review workflow, Verified Artist status.

### Phase 5 — Services, pricing, and availability
Artist service/pricing definition and availability management; surfaced on artist profiles for customers.

### Phase 6 — Booking and quotation
Booking request flow, quotation flow, booking state machine (per [system-architecture.md](system-architecture.md#6-booking-lifecycle)), booking oversight tooling for admins.

### Phase 7 — Payments
Payment provider abstraction and integration, deposit collection tied to booking confirmation, admin-mediated refund review.

### Phase 8 — Messaging and notifications
In-app messaging (customer-artist), push notifications (FCM) and email notifications for booking/message/verification events, background worker jobs for notification fan-out.

### Phase 9 — Reviews and reputation
Post-booking review submission, review display on artist profiles, admin moderation of reviews.

### Phase 10 — Admin dashboard completion and analytics
Full admin dashboard: user management, moderation queues, reports/disputes handling, platform analytics (PostHog-backed), system configuration screens.

### Phase 11 — Hardening and MVP launch readiness
Cross-cutting security review, load/performance pass, observability completeness (Sentry/PostHog coverage), accessibility pass on web/mobile, test coverage review for business-critical logic. This phase closes MVP scope.

### Phase 12 — Premium Customer tier
Subscription billing integration, premium feature gating (unlimited collections, priority booking, etc. per [feature-scope.md](feature-scope.md#2-post-mvp)).

### Phase 13 — AI-assisted discovery and photo preview
AI service integration behind the abstraction defined in [system-architecture.md](system-architecture.md), semantic design discovery, hand/foot photo preview.

### Phase 14 — Post-MVP marketplace trust features
Moderator role introduction, formal dispute-resolution workflow, follow-artist activity feed, artist earnings/payout automation.

### Phase 15+ — Future functionality
Scheduled and scoped individually as they're prioritized: generative AI design creation, AR live preview, loyalty program, video consultations, multi-currency/region, multi-artist studio accounts, public API, offline-first mobile.

## Current status

| Phase | Status |
|---|---|
| 0 | In progress (this document) |
| 1+ | Not started |

## Related documents

* [feature-scope.md](feature-scope.md)
* [system-architecture.md](system-architecture.md)
* [security-baseline.md](security-baseline.md)
