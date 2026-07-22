# MehndiVerse — Customer Design Gallery (Phase 7)

Status: Draft (Phase 7)
Last updated: 2026-07-14

This document covers the customer-facing design gallery — home feed, category browsing, design detail, and their shared backend concerns — introduced in Phase 7 on top of the catalog backend built in Phase 6.

## 1. Home feed

`GET /designs/home-feed` returns three sections in a single response — `latest`, `featured`, `trending` — each capped at 10 items, rather than three separate round trips. All three query the same `Design` table filtered to `status = 'published'`:

- **Latest**: `ORDER BY created_at DESC`.
- **Featured**: same, filtered to `is_featured = true`.
- **Trending**: `ORDER BY view_count DESC` — a foundation, not a real trending algorithm (no time-decay/window; a design's all-time view count is what's compared). A later phase can swap in a proper recency-weighted score without changing the endpoint's shape.

Both Flutter (`HomeScreen`) and web (`DiscoverView`) render this as three labeled rows/sections above a category-chip switcher.

## 2. Category browsing

`GET /designs/published` is the general-purpose, filterable, cursor-paginated listing endpoint — `category_id`, `difficulty_level`, `body_placement`, and `sort` (`latest` | `trending`) are all optional query params. Category browsing is just this endpoint with `category_id` set; there's no separate "browse" endpoint. Clients fetch `GET /categories` once to render filter chips, then re-issue this call with the selected category's id.

## 3. Cursor-based pagination

`GET /designs/published` uses keyset pagination, not `LIMIT/OFFSET` — see `app/core/pagination.py`. Offset pagination gets slower as the offset grows (the database still scans and discards every skipped row) and can skip or duplicate items if rows are inserted while a client pages through results. Keyset pagination instead remembers the sort key of the last row seen and asks for "everything strictly after that":

```
WHERE (created_at, id) < (:last_created_at, :last_id)  -- sort=latest
WHERE (view_count, id) < (:last_view_count, :last_id)  -- sort=trending
ORDER BY <same columns> DESC
LIMIT :limit
```

The `id` tiebreaker matters — `created_at` (or `view_count`) alone isn't unique, so ties would otherwise let a row appear twice or vanish across pages.

The cursor itself is an opaque base64 string encoding `sort|sort_value|id`. It's rejected (422) if replayed against a different `sort` than the one that issued it — switching from "Latest" to "Trending" mid-scroll always starts a fresh page rather than silently misinterpreting the old cursor's sort key as the new sort's.

Response envelope: `{ items: [...], page_info: { next_cursor, has_more } }`. Web paginates via a "Load more" button; Flutter does the same (a button, not scroll-triggered infinite load, to keep the loading state visible and the behavior identical across both clients).

## 4. Query optimization

Two things changed from Phase 6's straightforward implementation:

1. **Composite indexes** (`app/db/models/design.py`, migration `b225a8402428`) — `(status, created_at, id)`, `(status, is_featured, created_at)`, `(status, view_count, id)` on `designs`, and `(category_id)` on `design_categories`. Each leads with the column every gallery query filters on first, and each matches one of the three home-feed orderings or the category-browse join exactly.
2. **Batched summary lookups** (`_batch_primary_images` / `_batch_artist_summaries` in `app/api/routes/designs.py`) — building a page of `DesignSummaryOut` used to mean one query per design for its primary image and one per design for its artist info (N+1). Both are now single queries across the whole page (`WHERE design_id IN (...)` / `WHERE artist_profile_id IN (...)`), building an in-memory dict the per-design summary builder reads from. The home feed batches this once across the *union* of all three sections' designs, not once per section. `tests/designs/test_home_feed.py::test_home_feed_query_count_does_not_scale_with_design_count` asserts the query count stays low regardless of how many designs are in the feed.

## 5. Public visibility filtering

Unchanged from Phase 6's model, reused by every new endpoint: a design is visible to everyone once `published`; before that (or once `archived`/`flagged`), only its owner or staff (`moderator`/`admin`/`super_admin`) can see it — enforced as a 404, not a 403, so a stranger can't distinguish "exists but private" from "doesn't exist." `GET /designs/{id}/related` and `POST /designs/{id}/view` both check this before doing anything else, so neither leaks information about a design a caller isn't allowed to see.

## 6. Thumbnail selection

Every list/grid response (`DesignSummaryOut.thumbnail_url`) prefers `thumbnail_medium_url` over the full-resolution `image_url`, falling back to the original only if no medium thumbnail exists yet. This keeps grid payloads and client-side image decoding cheap — a home feed of 30 designs downloads 30 medium thumbnails, not 30 full-resolution originals. The design-detail view (`DesignOut`/`DesignImageOut`) still exposes the full `image_url` for the zoomed view. Only `ready` images are ever considered (`pending`/`processing`/`failed` images have no usable URL and are skipped).

## 7. View-count event handling

`POST /designs/{id}/view` increments `designs.view_count` atomically (`UPDATE ... SET view_count = view_count + 1`, never a Python read-modify-write, so concurrent viewers never lose an increment) — see `app/services/view_tracking.py`. A Redis key (`design_view:{design_id}:{viewer_id}`, 30-minute TTL, `SET NX`) deduplicates rapid repeat views from the same signed-in viewer, so reopening a design a few times in one sitting doesn't inflate its count. This is intentionally simple — no anonymous/IP-based dedup, no analytics window — a foundation for a later, more complete view-analytics phase. If Redis is unreachable, the dedup check fails open (skipped, increment still happens) rather than blocking the feature on a non-critical dependency. Viewing your own (unpublished) design never counts as a public view.

Both clients fire this as fire-and-forget immediately after a design's detail data loads successfully — a failed ping never surfaces an error to the viewer.

## 8. Safe caching foundation

`app/core/caching.py::set_public_cache()` sets `Cache-Control: public, max-age=N` on responses that are safe for a shared cache (CDN, corporate proxy, another visitor's browser) to reuse for *any* requester:

- Always safe on list/section endpoints (home feed, published list, related, categories) — they only ever return published (or globally-visible taxonomy) data, identical for everyone.
- On `GET /designs/{id}`, only when the design is actually `published`. An owner or moderator viewing a draft never gets this header — that response must never be cached and replayed to a different visitor.

This is a foundation, not a full caching layer: there's no CDN or edge cache configured yet, no cache invalidation on write, and no ETag/conditional-request support. It just makes sure that whenever a real cache *is* introduced in front of this API, it can trust these headers without a data-leak risk baked in from day one.

## 9. Design detail: gallery, zoom, artist summary, related designs

`GET /designs/{id}` (`DesignOut`) now includes an `artist: ArtistSummaryOut | None` (business name/avatar/headline/rating, resolved from the artist's `ArtistProfile` + Phase 5 `Profile`) alongside the existing images/categories/tags. `GET /designs/{id}/related` returns up to 10 other published designs sharing at least one category, excluding the design itself.

- **Web** (`components/gallery/image-gallery.tsx`): main image + thumbnail strip; clicking opens a native `<dialog>` zoom view.
- **Flutter** (`DesignImageGallery` in `gallery_widgets.dart`): main image + thumbnail strip; tapping opens a full-screen route with `InteractiveViewer` (pinch-to-zoom) and a swipeable `PageView` across all images.

## 10. Shareable design URLs

`/designs/[id]` (web) and `/design/:id` (Flutter, pushed on top of whichever shell is active) are stable, deep-linkable routes — visiting either always resolves to the same design. Both still require authentication (see [profile-and-privacy.md](profile-and-privacy.md) and [design-catalog.md](design-catalog.md) for why every endpoint has required auth since Phase 3): an unauthenticated visitor following a shared link is redirected to log in first (the same pattern `/account` already used), then lands on the design. True anonymous sharing (e.g. a link preview for someone not logged in at all) would require deciding on an anonymous-read API surface, which is explicitly out of scope here — this phase only guarantees the URL itself is stable and shareable *between* users of the app.

## 11. Client states

Both clients implement the same four states for every gallery view, per the phase brief:

- **Loading** — skeletons (web: `Skeleton`/`DesignGrid`'s built-in skeleton grid; Flutter: `AppLoadingView`).
- **Empty** — "no designs yet" / "no designs found" (never fake data).
- **Retry** — `ErrorState`/`AppErrorState` with a retry action, shown per-section on the home feed so one failed section doesn't block the other two.
- **Offline-friendly error** — web's `useOnlineStatus()` hook and Flutter's `GalleryRepository`'s `DioExceptionType.connectionError` detection both distinguish "you're offline" from a generic server error and show a distinct message.

**Image placeholders**: a design with no `thumbnail_url` yet (image still processing, or none uploaded) renders a plain placeholder icon instead of a broken image — `DesignCard` (web) and `DesignThumbnailCard` (Flutter).

**Accessible image descriptions**: every design image carries a generated description (`"{title} mehndi design by {artist}"`, or without the artist clause if there isn't one) — as the `alt` text on web's `next/image`, and as a `Semantics(label: ..., image: true)` node on Flutter's `Image.network` (with `excludeSemantics: true` so the caption text underneath isn't announced twice).

**Pull-to-refresh** (Flutter only, per the phase brief): `HomeScreen` wraps both the home-feed and category-browse views in a `RefreshIndicator`.

**Responsive web layout**: the design grid is a CSS grid (`grid-cols-2 sm:grid-cols-3 lg:grid-cols-4`, from Phase 4), and the design-detail page switches from a stacked to a two-column (`lg:grid-cols-2`) image/info layout at the `lg` breakpoint.

## 12. What Phase 7 deliberately does not do

Per the phase brief: no likes, saves, or comments — `Design.like_count` exists in the schema (Phase 2) but nothing in this phase reads or writes it beyond exposing the stored value. No anonymous/public API access. No real trending algorithm (time-decay, personalization) — view-count-only, as noted above. No CDN/edge cache — only the `Cache-Control` header foundation.

## 13. Related documents

- [design-catalog.md](design-catalog.md) — the Phase 6 backend this phase builds on (categories, design records, image upload pipeline)
- [profile-and-privacy.md](profile-and-privacy.md) — the artist profile/avatar data surfaced in `ArtistSummaryOut`
- [design-system.md](design-system.md) — the shared design tokens/components (`DesignGrid`, `AppEmptyState`, etc.) this phase reuses
