# MehndiVerse — Product Analytics and Recommendations (Phase 22)

Phase 22 adds a general-purpose product-analytics event log (`AnalyticsEvent`) covering the full list of events product/growth teams need, plus a set of recommendation and reporting calculations built on top of it: trending designs, popular artists, recently viewed designs, category-based and similar-design recommendations, a basic personalized home feed, search analytics, booking-conversion analytics, and admin-facing views over all of it.

## Privacy-safe analytics event schema

`app/db/models/analytics.py::AnalyticsEvent` — one append-only table, `app/services/analytics/events.py::record_event()` the only function that ever writes to it. Columns: `user_id` (nullable, `SET NULL` on delete), `session_id` (for guest/pre-login activity), `event_type` (a `CHECK`-constrained `AnalyticsEventType` value), a polymorphic `entity_type`/`entity_id` pair (the same pattern `AiGeneration`/`Report` already use — one column pair covers every entity kind an event might be about instead of a wide table of mostly-null foreign keys), `properties` (a JSONB bag for event-specific supplementary data), and `created_at`.

### Track events for

The full Phase 22 event list and how each is recorded:

| Event | `AnalyticsEventType` value | How it's recorded |
|---|---|---|
| App opened | `app_opened` | Client-reported — `POST /analytics/events` |
| Registration completed | `registration_completed` | Server — `app/api/routes/auth.py::register` |
| Design viewed | `design_viewed` | Server — `app/services/view_tracking.py::record_design_view` |
| Design liked | `design_liked` | Server — `app/services/engagement.py::like_design` |
| Design saved | `design_saved` | Server — `app/services/engagement.py::add_item_to_collection` (default collection only) |
| Search performed | *(not a new event type — see [Search analytics](#search-analytics))* | Server — the pre-existing `SearchEvent` table |
| Filter applied | *(not a new event type — see [Search analytics](#search-analytics))* | Server — `SearchEvent.filters` on the same row |
| Artist viewed | `artist_viewed` | Server — `app/api/routes/artists.py::get_artist` |
| Booking started | `booking_started` | Server — `app/services/booking.py::create_draft_booking` |
| Booking submitted | `booking_submitted` | Server — `app/services/booking.py::submit_booking` |
| Quote accepted | `quote_accepted` | Server — `app/services/booking.py::accept_quote` |
| Payment completed | `payment_completed` | Server — `app/services/payments/service.py::_settle_payment`/`_settle_subscription_payment` |
| Subscription started | `subscription_started` | Server — `app/services/subscriptions.py::activate_or_renew_subscription` (first activation only, not renewals) |
| AI generation requested | `ai_generation_requested` | Server — `app/services/ai/generations.py::create_ai_generation` and `app/services/ai/design_generation.py::create_design_request` |
| Preview created | `preview_created` | Server — `app/services/previews.py::create_preview` |
| Design shared | `design_shared` | Client-reported — `POST /analytics/events` |

Client-reported events are restricted to an allow-list (`app/api/routes/analytics.py::_CLIENT_REPORTABLE_EVENT_TYPES` = `app_opened`, `design_shared`) — every other event type is rejected with `422` if a client tries to report it, since the server already records it automatically at its own call site and would otherwise double-count it.

**Why `search_performed`/`filter_applied` aren't `AnalyticsEvent` rows**: this codebase already had a dedicated `SearchEvent` table (Phase 8/9, `app/db/models/search.py`) logging every search request's query text, active filters, and result count — the exact same information a `search_performed`/`filter_applied` event would carry. Rather than duplicate that into a second, parallel event stream, [search analytics](#search-analytics) reads `SearchEvent` directly.

**Why this replaces Phase 20's `RecommendationEvent`**: that table (`view`/`like`/`save`/`search_click`/`booking_request`) was explicitly scoped as collection-only in Phase 20, with no consumer — "this phase only *collects*; nothing reads this table to actually recommend anything yet" was its own docstring. This phase is the first to actually compute anything from collected events, and needed a schema broad enough for general product analytics, not just recommendation inputs, so `AnalyticsEvent` replaces it outright (see the migration `3e799ebff530_analytics_events_and_recommendations.py`) rather than running two overlapping event logs side by side.

### Do not place sensitive personal information in analytics payloads

Three layers:

1. **Schema design**: nothing about `AnalyticsEvent` stores or requires personal data — `entity_id` is an opaque UUID reference, not a name/email/address.
2. **Call-site discipline**: every `record_event(...)` call site in this codebase passes only coarse, non-identifying `properties` (a plan slug, a payment type, a style/occasion string) — never a raw email, phone number, name, address, payment-card number, or message body.
3. **`record_event`'s own denylist** (`app/services/analytics/events.py::_DENYLISTED_PROPERTY_KEYS`): a defense-in-depth key-name filter that silently drops any property whose key looks like `email`/`phone`/`name`/`address`/`card_number`/`message`/etc., plus a length cap (`_MAX_PROPERTY_VALUE_LENGTH`) truncating anything unexpectedly large. This catches an accidental mistake at a future call site; it is not a substitute for writing safe call sites in the first place.

## Provide analytics consent where legally required

`UserPreference.analytics_consent` (default `False`, mirroring this table's existing `marketing_opt_in`'s opt-in-required precedent rather than assuming consent) — surfaced via the existing preferences endpoints, `GET`/`PATCH /users/me/preferences`.

`record_event()` checks it on every call that includes a `user_id`: if that user has not set `analytics_consent = True`, the event is still recorded (its anonymous signal — "a design was viewed" — still has aggregate analytical value) but with `user_id` dropped, keeping only `session_id` if the caller supplied one. **A non-consenting user's identity is never attached to a stored event.** This has a real, honest consequence documented at the call sites that rely on it: `get_recently_viewed_designs(user_id=...)` returns nothing for a user who has never consented, because their `design_viewed` events were never stored with their `user_id` in the first place — there's no separate "personalization without consent" backdoor.

This is a foundation-level consent mechanism (a stored flag, checked before every identified write), not a full legal-compliance engine — a real deployment layering region-specific requirements (e.g., an EU cookie-consent banner) on top would gate the *client's* decision to call `PATCH /users/me/preferences` in the first place; the server-side enforcement here is what makes that gate actually mean something.

## Allow analytics to be disabled

Two independent layers, both of which must allow an event through:

- **Operator-level, global**: `app/services/analytics/flags.py::is_analytics_enabled()` reads `SystemSetting` key `analytics.enabled` — the same `SystemSetting`-backed flag mechanism `app/services/ai/flags.py` already established for AI features. Defaults enabled (a fresh environment collects analytics until an operator deliberately turns it off, via the existing `admin_settings.py` surface). When off, `record_event()` returns `None` immediately and writes nothing at all, for any event, from any user.
- **User-level, per-identity**: `UserPreference.analytics_consent` (see above) — doesn't stop the event being recorded, but stops it being *attributable* to that user.

## Trending-design calculation

`app/services/analytics/recommendations.py::get_trending_designs()` — weighted engagement **within a recent time window** (default 7 days), not lifetime popularity. Weights: `design_viewed` = 1, `design_liked` = 3, `design_saved` = 5 (a save signals stronger intent than a like, which signals stronger intent than a view). Only published, non-deleted designs are ever returned.

This is deliberately distinct from `app/api/routes/designs.py::get_home_feed`'s pre-existing "trending" section (Phase 7), which is a simple lifetime `Design.view_count DESC` sort — unaffected by this phase. A design published years ago with a huge lifetime view count isn't "trending" today; a design that suddenly got a burst of engagement this week is, even with a small lifetime total. The two coexist: Phase 7's home feed still works exactly as before, and this phase's richer, actually-personalized feed lives at a new endpoint (see [Basic personalized home feed](#basic-personalized-home-feed)).

## Popular-artist calculation

`app/services/analytics/recommendations.py::get_popular_artists()` — blends a recency signal (`artist_viewed` events in the last `window_days`, default 30 — longer than trending designs' 7, since an artist's reputation builds and stays relevant over a longer horizon than one design's viral moment) with the durable trust signals this codebase already maintains on `ArtistProfile` itself:

```
score = (rating_average * ln(1 + rating_count)) + (follower_count * 0.5) + (recent_artist_views * 1.0)
```

`rating_average * ln(1 + rating_count)` rewards both quality and a track record of *enough* reviews to trust that rating (a single 5-star review scores far lower than a hundred 4.8-star ones); follower count and recent profile views are lighter-weight signals added on top, not the dominant term. Only `approved` (verified), non-deleted artist profiles are considered.

## Recently viewed designs

`app/services/analytics/recommendations.py::get_recently_viewed_designs()` — reads a viewer's own `design_viewed` events back, deduplicated per design, most recent first. Works by `user_id` (an authenticated viewer) or `session_id` (a guest, if a client supplies one); returns an empty list if neither is given. See [Provide analytics consent](#provide-analytics-consent-where-legally-required) for why a non-consenting user gets nothing here.

## Category-based recommendations

`app/services/analytics/recommendations.py::get_category_based_recommendations()` — infers up to 3 categories a user engages with most (same view=1/like=3/save=5 weighting as trending, over a 90-day lookback), then recommends other published designs in those categories the user hasn't already interacted with, ordered by lifetime `like_count`. A simple, explainable "people who liked X also tend to like other things in the same category" heuristic — not a trained collaborative-filtering model. Returns an empty list for a user with no engagement history, which callers use as the signal to fall back to trending/latest content (see [Add fallback content for new users](#add-fallback-content-for-new-users)).

## Similar-design recommendations

Reused verbatim from Phase 20, not reimplemented: `app/services/ai/similarity.py::find_similar_designs()` (embedding-based cosine similarity over `DesignEmbedding`), exposed at `GET /designs/{id}/ai/similar`. `app/services/analytics/recommendations.py::get_similar_designs()` is a one-line pass-through kept in this package purely so every recommendation capability has one obvious home, even though the actual computation lives in `app/services/ai/`.

## Basic personalized home feed

`GET /analytics/home-feed` (`app/services/analytics/recommendations.py::get_personalized_home_feed()`) blends three sections:

- `recently_viewed` — this viewer's own recent `design_viewed` history.
- `recommended_for_you` — category-based recommendations from their engagement history (always empty for a guest with no `user_id`).
- `trending` — always populated; see [fallback](#add-fallback-content-for-new-users).

`is_personalized` tells a client whether `recently_viewed`/`recommended_for_you` actually reflect this viewer, or are empty fallback-only sections — useful for a client deciding whether to show a "personalized for you" label or a generic "popular right now" one.

This is a new, separate endpoint from Phase 7's `GET /designs/home-feed` (`latest`/`featured`/`trending` sections, still unchanged) — see [Trending-design calculation](#trending-design-calculation) for why the two "trending" concepts deliberately differ, and why this phase didn't touch the existing endpoint.

## Add fallback content for new users

Every recommendation surface in this phase is designed so a brand-new user (or a brand-new platform with no engagement history at all) never sees an empty result:

- [Category-based recommendations](#category-based-recommendations) returns `[]` for no history — callers treat that as "fall back to trending," not an error.
- [Personalized home feed](#basic-personalized-home-feed)'s `trending` section, if trending itself has no signal yet (a quiet window or a day-one platform with zero events), falls back further to the newest published designs (`ORDER BY created_at DESC`) — so the feed is never empty even before a single `AnalyticsEvent` row exists.
- [Recently viewed](#recently-viewed-designs) legitimately *can* be empty for a new user (there's nothing to fall back to for "your own view history" — an empty list is the correct, honest answer) — client UIs should simply hide that section rather than show a fake substitute.

## Search analytics

`app/services/analytics/search_analytics.py::get_search_analytics_summary()` reads the pre-existing `SearchEvent` table (see [Track events for](#track-events-for) above for why no new event stream was added). Reports, over a window (default 30 days): `total_searches`, `zero_result_searches`/`zero_result_rate`, and `top_queries` (the most frequent non-blank keyword searches). `zero_result_rate` is the single most actionable search-quality metric a foundation needs — a consistently high rate points at either a catalog gap or a search-provider relevance problem, either way something staff should look at.

## Booking-conversion analytics

`app/services/analytics/booking_analytics.py::get_booking_conversion_funnel()` — an event-count funnel over `AnalyticsEvent`: `booking_started` → `booking_submitted` → `quote_accepted` → `payment_completed`, over a window (default 30 days). `stage_conversion_rates` divides each stage's count by the *previous* stage's count; `overall_conversion_rate` divides `payment_completed` by `booking_started` — the single top-line "does a started booking end in a paid booking" number. This deliberately counts *events*, not distinct bookings tracked through every stage in order — a lightweight foundation metric, not a full per-booking cohort/attribution analysis.

## Admin analytics views

`app/api/routes/admin_analytics.py`, gated to `moderator`/`admin`/`super_admin` (the same `_VIEW_ROLES` split every other admin-reporting route in this codebase uses — nothing here mutates anything, so there is no separate edit-role split):

- `GET /admin/analytics/trending-designs`
- `GET /admin/analytics/popular-artists`
- `GET /admin/analytics/search`
- `GET /admin/analytics/booking-conversion`

## API surface

- `POST /analytics/events` — client-reported events (`app_opened`, `design_shared` only).
- `GET /analytics/recently-viewed` — the caller's own recently viewed designs.
- `GET /analytics/recommended` — category-based recommendations for the caller.
- `GET /analytics/home-feed` — the personalized home feed.
- `GET /designs/{id}/ai/similar` — similar-design recommendations (Phase 20, reused).
- `GET`/`PATCH /users/me/preferences` — now also exposes `analytics_consent`.
- `GET /admin/analytics/*` — the four admin reporting views above.

## What this phase deliberately does not do

- **No trained recommendation model.** Every calculation here is an explainable, hand-specified heuristic (weighted recent engagement, category co-occurrence, embedding cosine similarity) — not collaborative filtering or a learned ranking model.
- **No third-party analytics/ad-tracking integration.** This is entirely first-party, stored in this application's own database.
- **No per-booking cohort funnel.** Booking-conversion analytics counts events per stage, not individual bookings traced end-to-end.
- **No client-side event batching/offline queue.** `POST /analytics/events` is a single synchronous call per event; a mobile client's offline-queueing strategy is its own concern.

## Related documents

- docs/ai-foundation.md — the `SystemSetting`-backed feature-flag pattern [Allow analytics to be disabled](#allow-analytics-to-be-disabled) reuses, and the embedding-based similarity search [Similar-design recommendations](#similar-design-recommendations) reuses.
- docs/design-search.md — `SearchEvent`, the table [Search analytics](#search-analytics) reads.
- docs/profile-and-privacy.md — `UserPreference`'s existing consent-adjacent fields, the precedent `analytics_consent` follows.
