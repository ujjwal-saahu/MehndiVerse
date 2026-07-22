# MehndiVerse — Artist Public Profiles, Portfolios, and Services (Phase 11)

Status: Draft (Phase 11)
Last updated: 2026-07-18

This document covers the customer-facing artist directory/profile, self-service portfolio management, and self-service bookable services — introduced in Phase 11 on top of the onboarding/verification lifecycle from Phase 10. Portfolio create/edit/archive/image-upload/categories already existed as a backend (Phase 6/7's `designs.py`) with no client ever wired to it; this phase builds that client for the first time, alongside everything that's genuinely new (directory, public profile, services, follow, analytics).

## 1. Directory visibility

`PUBLIC_DIRECTORY_STATUSES = {submitted, under_review, approved}` (`app/services/artist_directory.py`) — `draft`/`rejected`/`suspended`/`more_information_required` artists have no public presence at all. `GET /artists` defaults `verified_only=true`, showing only `approved` artists; setting it `false` also surfaces `submitted`/`under_review` artists (still pending, shown without the verification badge) — this is what gives the "verified-only filter" real meaning rather than being a no-op toggle, since the directory's population genuinely differs between the two settings.

`GET /artists/{id}` mirrors `designs.py`'s 404-vs-403 visibility convention exactly: a stranger requesting a non-public profile gets **404** (existence hidden), while the owner or staff can always view it regardless of status (e.g. to preview before submitting).

## 2. Public profile vs. owner profile

`ArtistPublicProfileOut` (`app/schemas/artist_directory.py`) is a deliberately separate schema from the private `ArtistProfileOut` (`app/schemas/artist.py`, Phase 10) — it excludes contact email/phone, verification internals (`submitted_at`, `rejection_reason`, `missing_requirements`, ...), and anything else that's owner/staff-only. It adds what the private schema doesn't need: `is_verified` (derived from `verification_status == approved`), `follower_count`/`is_followed`, active `services`, an `availability_preview`, and a `portfolio_preview` (+ `portfolio_count`).

## 3. Portfolio management listing

`GET /designs/mine` (new in this phase, `designs.py`) is the artist's own management listing — every status (draft/published/archived/flagged), not just published, cursor-paginated by `created_at DESC` with an optional `status_filter`. This is distinct from `GET /designs/published?artist_profile_id=...` (also new this phase), which is the public, published-only view of a specific artist's portfolio, reused by both the profile page's "view all" link and any other published-portfolio browsing. Registered *before* `GET /designs/{design_id}` in the router — FastAPI matches routes in registration order, so a literal path must precede a `{design_id}: UUID` catch-all or it would shadow it and fail UUID validation on the literal segment.

## 4. Portfolio create/edit/archive/images/categories/premium

All of this was already fully built server-side in an earlier phase (`app/api/routes/designs.py`) — create, partial update, archive, category/tag sync, and the authorize-then-upload image pipeline (see docs/design-catalog.md#image-upload-pipeline). Phase 11 wires a client to it for the first time (web: `/artist/portfolio`, `/artist/portfolio/new`, `/artist/portfolio/{id}/edit`) and adds one permission rule that didn't previously exist:

### Premium status permission

Only a `verified_artist` (`ArtistProfile.verification_status == approved`) or staff may set `is_premium: true`, on both create and update (`_PREMIUM_ROLES` in `designs.py`). An artist who hasn't been approved yet can't gate content behind a trust signal nobody has vetted. Turning premium **off** is always allowed regardless of role — only the upgrade is gated, never the downgrade. `DesignCreateRequest` gained an `is_premium` field (previously settable only via update) so this can be set at creation time too.

## 5. Services

`ArtistService` (Phase 2 schema) previously had no route file touching it at all. This phase adds full self-service CRUD (`app/api/routes/artist_services.py`, prefix `/artist/services`) plus the four fields the phase spec calls for that the model didn't yet have: `customer_capacity`, `deposit_required`/`deposit_amount`, `travel_charge_amount`, `cancellation_policy` (migration `de1b95efd1f0`).

Open to any `artist`/`verified_artist` — **not** gated on verification status, mirroring `designs.py`'s `_CREATE_ROLES` precedent (an artist can draft their service list before approval, the same way they can draft portfolio designs). No staff-on-behalf-of creation (unlike designs, a "platform-curated service" isn't a meaningful concept) and no hard-delete endpoint — `is_active` toggling is the only "removal" path, consistent with the model's `SoftDeleteMixin` never being exposed as a delete action in this phase.

Pricing shape must match `pricing_type` (`fixed` → `price_amount` only; `range` → `price_min`+`price_max` only; `custom_quote` → none of the three) — validated by `validate_pricing_consistency()`, shared between the create schema's `model_validator` (whole payload at once) and the update route (re-run after merging a partial payload onto the existing row, since a partial update alone can't be validated in isolation).

## 6. Follow foundation

`Follow` (Phase 2 schema, unused until now — same pattern as `AuditLog` before Phase 10) is wired up with the identical "insert, then treat a unique-constraint conflict as already-done" idempotent pattern `app/services/engagement.py` established for likes/saves (`app/services/artist_directory.py::follow_artist`/`unfollow_artist`). `ArtistProfile.follower_count` is a new denormalized counter (migration `de1b95efd1f0`), atomically incremented/decremented — mirroring `Design.like_count`/`save_count`'s pattern rather than a live `COUNT()` at read time, since this phase's follow read+write path is fully built (unlike `rating_average`/`rating_count`, which stay at their Phase 2 zero-value defaults until a future reviews phase populates them). Following yourself is rejected (`422`).

## 7. Booking CTA foundation

No booking flow exists yet — the CTA is deliberately just a signal: both clients show a "Request a booking" button gated on `ArtistProfile.is_accepting_bookings`, with no backend action wired to it. This establishes the UI surface a future booking phase will attach real behavior to, the same way this phase found `Follow`/`follower_count`-shaped groundwork already laid by Phase 2.

## 8. Portfolio analytics foundation

`GET /artist/portfolio/analytics` (self-service, `artist_onboarding.py` — grouped with the artist's other self-service actions rather than a new file for one endpoint) returns aggregate counts (`total_designs`, `published_designs`, `total_views`, `total_likes`, `total_saves`) plus a top-5-by-views list. Explicitly a foundation: no time-series data, no date bucketing, no per-design historical trend — those require a events/facts table this phase doesn't introduce.

## 9. Directory filters

`GET /artists` — `city`/`country` (substring/exact match), `service` (substring match against the artist's own active service names — foundation-level, not a full-text/category search), `min_rating`, `verified_only` (see §1), cursor-paginated by `rating_average DESC, id DESC`.

## 10. Client implementations

- **Web**: `/artists` (directory) and `/artists/{id}` (profile, with a "view all" link to `/artists/{id}/portfolio` for the full paginated gallery when the preview doesn't show everything). Self-service: `/artist/portfolio` (list/create/edit/archive/analytics link) and `/artist/services`. A `FollowButton` component (optimistic toggle + rollback, matching the existing like/save pattern from docs/engagement-and-collections.md#optimistic-ui-with-rollback) is used on the profile page. All backend calls go through `src/app/api/artists/*`, `src/app/api/artist/services/*`, `src/app/api/artist/portfolio/analytics`, and extended `src/app/api/designs/*` proxy routes.
- **Flutter**: `ArtistDirectoryScreen` and `ArtistPublicProfileScreen` (with the same optimistic follow toggle), reached via a "Find an artist" icon on the Discover tab's app bar (same treatment as Phase 8's search icon) and pushed routes exempted from the artist/customer shell-gating redirect. Self-service portfolio/services management screens are **not** built on Flutter in this phase — the web app already covers artist-side management end-to-end, and mobile-specific management UI for create/edit/image-upload/service-CRUD was judged lower-value than the customer-facing directory/profile given the effort available; this can be picked up in a later phase if needed.

### A router bug this phase's own routes exposed

The Flutter router's existing artist/customer shell-gating check was a bare `state.matchedLocation.startsWith('/artist')`, which — before this phase — never had to distinguish `/artist` from `/artists` because no `/artists`-prefixed route existed. Adding the public directory at `/artists` would have been wrongly caught by that check (`"/artists".startsWith("/artist")` is `true`) and bounced customers back to `/` before ever reaching it. Fixed to `matchedLocation == '/artist' || matchedLocation.startsWith('/artist/')`, which correctly excludes `/artists`.

## 11. Query and permission tests

- `tests/artist/test_directory.py` — auth requirement, default verified-only population, `verified_only=false` widening, city/country/service/min-rating filters, pagination.
- `tests/artist/test_public_profile.py` — 404-vs-owner-visibility for non-public profiles, full response shape (services/portfolio/availability/follow state), full-portfolio-via-`/designs/published`, follow/unfollow (idempotency, no-op unfollow, self-follow rejection).
- `tests/artist/test_services.py` — role/ownership requirements, pricing-shape validation for all three pricing types (including the merge-then-revalidate path on update), activate/deactivate, cross-artist ownership rejection.
- `tests/artist/test_portfolio_analytics.py` — aggregation correctness (including that another artist's designs never leak into the total), zero-state.
- `tests/designs/test_my_designs.py` — every-status-but-only-the-owner's listing, status filter, pagination.
- `tests/designs/test_design_create.py`/`test_design_update_and_ownership.py` — premium-permission gate (verified artist can set it, unverified artist is rejected but can still turn it off).

## 12. What Phase 11 deliberately does not do

No reviews/ratings writing (the `rating_average`/`rating_count` columns are read-only in this phase, same Phase 2 placeholder they've always been — a future reviews phase populates them, mirrored by Phase 10's identical treatment of `AuditLog` before it was wired up). No booking flow behind the CTA (§7). No availability *management* — only the read-only preview the phase spec asks for; there is still no way for an artist to create an `ArtistAvailability` row, so the preview will be empty until a future phase adds that. No service deletion, only activate/deactivate. No rating filter beyond a simple `min_rating` threshold (no distribution/histogram — "foundation" per the phase spec). No Flutter self-service portfolio/services management (§10).

## 13. Related documents

- [artist-verification.md](artist-verification.md) — the Phase 10 onboarding/verification lifecycle this phase's `is_verified`/`PUBLIC_DIRECTORY_STATUSES` build on
- [design-gallery.md](design-gallery.md) — the Phase 7 `designs.py` visibility/pagination conventions this phase's portfolio endpoints reuse
- [design-catalog.md](design-catalog.md) — the image-upload pipeline the portfolio management UI is the first client of
- [engagement-and-collections.md](engagement-and-collections.md) — the idempotent-insert and optimistic-UI-with-rollback patterns this phase's follow feature reuses
