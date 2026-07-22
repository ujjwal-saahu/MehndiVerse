# MehndiVerse — Feature Scope (MVP / Post-MVP / Future)

Status: Draft (Phase 0)
Last updated: 2026-07-14

This document sequences the requirements from [product-requirements.md](product-requirements.md) into delivery tiers. Tier placement drives the phase ordering in [development-roadmap.md](development-roadmap.md); nothing here is scheduled to a date.

Tiering principle: **MVP** is the smallest set of features that lets a customer complete the full loop (discover → book → pay deposit → get served → review) and lets an artist run their side of that loop, with the minimum admin tooling needed to keep it safe (verification, moderation, refund oversight). **Post-MVP** enhances retention, trust, and monetization. **Future** is directional and not committed.

## 1. MVP

### Guest / Customer
* Registration and login (Supabase Auth).
* Browse, search, and filter the design catalog.
* View design detail pages.
* Like and save designs.
* Basic collections (single default collection or capped count).
* View artist portfolios and profiles.
* Submit a booking request to an artist.
* Receive and accept/decline a quotation.
* Pay a booking deposit via the abstracted payment provider.
* In-app messaging tied to a booking.
* Push and email notifications for booking status changes.
* Leave a review after a completed booking.

### Artist
* Registration and profile creation.
* Submit verification documents.
* Upload portfolio items.
* Define services and pricing.
* Set basic availability.
* Receive booking requests and respond with quotations.
* In-app messaging with customers.
* View own booking history and reviews.

### Administrator
* User account management (view/suspend/delete).
* Artist verification review (approve/reject).
* Design/portfolio moderation (approve/remove/flag).
* Category and taxonomy management.
* Booking oversight (view all, intervene).
* Payment/refund review (manual refund processing).
* Basic platform analytics (signups, bookings, GMV-equivalent).

### Platform / cross-cutting
* Flutter mobile app covering the customer and artist MVP flows above.
* Next.js customer web app covering the browse/booking flows above.
* Next.js admin dashboard covering the administrator flows above.
* FastAPI backend with server-side authorization for all of the above.
* Sentry error monitoring and PostHog product analytics wired in from the start.
* `.env.example` and secret-handling conventions established per [security-baseline.md](security-baseline.md).

**Explicitly out of MVP**: Premium Customer tier, Verified Artist badge/ranking logic, Moderator role (Administrator covers moderation at MVP), AI design discovery, AI photo preview, follow-artist activity feeds, automated payouts, dispute workflow beyond manual admin handling, multi-language support.

## 2. Post-MVP

* Premium Customer subscription tier: paid plan, billing integration, unlimited collections, priority booking, ad-free / early-access perks.
* Verified Artist status as a distinct, badge-visible tier separate from baseline Artist (ranking/visibility boost in search).
* AI-assisted design discovery (semantic/visual search over the catalog).
* AI hand/foot photo preview (design overlay on a customer photo).
* Follow artists + followed-artist activity feed.
* Moderator role introduced as a distinct staff role, splitting moderation load off Administrators.
* Formal dispute-resolution workflow (structured case, evidence, resolution states) beyond ad-hoc admin handling.
* Artist earnings dashboard with payout automation (vs. manual admin-mediated payouts at MVP).
* Advanced availability (calendar sync, recurring schedules, blackout automation).
* Multiple payment providers and automated/self-service refund flows within policy limits.
* Notification preference center (granular opt-in/opt-out per channel and event type).
* Collaborative/shareable collections.
* Subscription/plan management for artists (paid visibility boosts), managed by Administrators.
* Localization / multi-language support.

## 3. Future (directional, not committed)

* Generative AI custom mehndi design creation.
* Real-time AR camera preview (live overlay, not static photo).
* Loyalty and rewards program.
* Video consultations between customer and artist.
* Multi-currency / multi-region expansion.
* Multi-artist studio/franchise accounts.
* Public API for third-party integrations.
* Offline-first mobile experience with background sync.

## 4. Scope change process

Any move of a feature between tiers, or addition of a new feature, should update this document and, if it changes role permissions, [user-roles-and-permissions.md](user-roles-and-permissions.md) in the same change — the two must not drift out of sync.

## 5. Related documents

* [product-requirements.md](product-requirements.md)
* [user-roles-and-permissions.md](user-roles-and-permissions.md)
* [development-roadmap.md](development-roadmap.md)
