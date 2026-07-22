# MehndiVerse — Design Search and Filtering (Phase 8)

Status: Draft (Phase 8)
Last updated: 2026-07-14

This document covers design search — keyword search, faceted filtering, sort, suggestions, search history, and their shared backend concerns — introduced in Phase 8 on top of the gallery backend built in Phase 7.

## 1. Search-provider abstraction

`app/services/search/` is deliberately layered so the route code never depends on how search is actually executed:

- `base.py` — the `SearchProvider` abstract base class (`search()`, `suggest()`), plus provider-agnostic value types: `SearchFilters`, `SearchPage` (ordered design ids + cursor, not hydrated summaries), `SuggestionHit`.
- `postgres_provider.py` — `PostgresFullTextSearchProvider`, the only concrete implementation today.
- `factory.py` — `get_search_provider()`, selected by the `search_provider` setting (`"postgres"` today). This is the *only* place that needs to change to add a Typesense or Meilisearch provider later — routes call `get_search_provider()` and never import `postgres_provider.py` directly.

The provider returns ids only; `app/api/routes/search.py` turns those back into `DesignSummaryOut`s via the same `app/services/design_summaries.py` helpers Phase 7's `/designs/published` and `/designs/home-feed` already use (extracted from `designs.py` in this phase specifically so `search.py` could reuse it without duplicating the batched image/artist lookups).

## 2. PostgreSQL full-text search

`designs.search_vector` is a generated (`GENERATED ALWAYS AS ... STORED`) `tsvector` column — `to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))` — maintained by Postgres itself on every insert/update, so it can never drift out of sync with the row. A GIN index (`ix_designs_search_vector`) makes `@@` lookups against it fast.

Raw user input is parsed with `websearch_to_tsquery('english', query)`, not `to_tsquery()` — the `websearch_to_tsquery` function is purpose-built for untrusted, free-form search strings (handles quotes and stray operators gracefully instead of raising a syntax error), where `to_tsquery` expects strict operator syntax a raw query could easily break.

Relevance ranking uses `ts_rank(search_vector, tsquery)`. When no keyword is given, `sort=relevance` falls back to `sort=newest` (there's nothing to rank against), the same fallback pattern Phase 7's trending-without-a-query home feed section uses.

## 3. Search criteria

`GET /designs/search` accepts:

| Param | Maps to |
|---|---|
| `q` | keyword, matched against `search_vector` |
| `category_id` (repeatable, max 20) | style / occasion / body_part / difficulty / density / region — see §4 |
| `artist_id` | `Design.artist_profile_id` |
| `is_premium` | `Design.is_premium` |
| `difficulty_level` | `Design.difficulty_level` (direct column, not the `difficulty` category axis — see note in §4) |
| `body_placement` | `Design.body_placement` (direct column, not the `body_part` category axis) |
| `sort` | `relevance` \| `newest` \| `popular` \| `most_saved` |
| `cursor`, `limit` | pagination — see §5 |

`difficulty_level`/`body_placement` exist as both a taxonomy axis (categories a design is tagged with, e.g. "Beginner Friendly") *and* a first-class column on `Design` (a single definite value) — this dual representation already existed for Phase 6/7's `/designs/published`, and Phase 8's search endpoint mirrors it rather than introducing a third scheme. The web/Flutter filter panels only surface the category-axis checkboxes (covering all six taxonomy axes, including difficulty/body_part) to avoid two visually separate "Difficulty" controls; the column-level params remain available in the API for any future client that wants finer-grained filtering.

## 4. Category filter semantics

Multiple `category_id` values are grouped by their `category_type` (the taxonomy axis) before querying: options **within** one axis are OR'd, but different axes are AND'd together. Picking "Bridal" (occasion) and "Beginner Friendly" (difficulty) requires *both*; picking "Bridal" and "Kids" (both `occasion`) requires *either*. Implemented as one `aliased(DesignCategory)` join per axis group in `postgres_provider.py::_apply_category_filters` — simpler than a `HAVING COUNT(DISTINCT ...)` approach and just as correct for a bounded number of axes.

## 5. Search-result pagination

Reuses Phase 7's keyset-pagination cursor (`app/core/pagination.py`), extended to support a float-valued "relevance" cursor alongside the existing datetime/int-based ones. The cursor is issued per-sort and rejected (422) if replayed against a different sort — same rule as `/designs/published`.

One deliberate simplification: relevance ranking is `ts_rank(...)`, a floating-point score. The cursor encodes it to 10 decimal places; re-parsing that string back to a float for the next page's `WHERE` clause carries a theoretical, extremely small risk of a boundary row being skipped or repeated if two designs' ranks differ only past the 10th decimal. This is noted rather than engineered around — full protection would mean projecting and comparing the exact in-database float end-to-end, adding real complexity for a case that in practice never occurs with `ts_rank`'s actual value distribution.

## 6. Search suggestions

`GET /designs/search/suggestions` does three independent prefix-match (`lower(column) LIKE 'prefix%'`) queries — against `designs.title` (published only, ordered by `view_count DESC`), `categories.name` (active only), and `artist_profiles.business_name` (non-null only) — and merges the results into one flat, capped list. A functional index (`ix_designs_title_lower_pattern`, `lower(title) text_pattern_ops`) keeps the title lookup index-backed without needing the `pg_trgm` extension. A minimum query length (2 characters, enforced both client-side and effectively by the tiny result set a 1-character prefix would otherwise scan) keeps this cheap.

Suggestions are whole-value prefix matches, not per-word: searching "henna" won't suggest a design titled "Bridal Henna Set" (title starts with "Bridal"), only one titled "Henna ...". This is a deliberate scope boundary for the Postgres-based foundation, not a bug — a future Typesense/Meilisearch provider would naturally support per-word/fuzzy matching without changing the route layer, per §1.

## 7. Search history, recent searches, and the analytics-event foundation

One table, `search_events`, serves both requirements rather than two separate ones: every call to `GET /designs/search` inserts a row (`user_id`, `query`, `filters` as JSONB, `result_count`, `created_at`) — including filter-only searches with no keyword, which is what makes it a real analytics-event log and not just a recent-searches cache. "Recent searches" (`GET /designs/search/history`) reads the same table back, filtered to rows where `query IS NOT NULL`, deduplicated case-insensitively, newest first, capped at 10. `DELETE /designs/search/history` clears a user's own rows.

Consequence: a filter-only search (no keyword) is logged for analytics but never shows up in "recent searches" — there's no keyword to show.

## 8. Sanitizing and bounding search input

`app/core/search_sanitize.py::sanitize_search_query()` strips control characters, collapses whitespace, and truncates to 200 characters before the query ever reaches `websearch_to_tsquery`. This isn't a SQL-injection defense (SQLAlchemy's parameterized queries already prevent that structurally) — it's about not letting a pathological input (a huge string, embedded control characters) become an expensive or nonsensical query.

"Prevent expensive uncontrolled queries" is enforced at a few layers:

- `limit` is clamped to `[1, 100]` server-side regardless of what a client requests.
- `category_id` is capped at 20 per request — an unbounded list would mean an unbounded number of joins.
- `sort`, `difficulty_level`, and `body_placement` are validated against fixed allow-lists (422 on anything else) rather than passed through to the query unchecked.
- `search_rate_limit` (`30/minute` by default, via the same `slowapi` limiter Phase 3's auth endpoints use) applies to `/designs/search` and `/designs/search/suggestions`.
- The GIN index on `search_vector` and the composite `(status, view_count/save_count, id)` indexes mean every sort mode has an index to lean on rather than a sequential scan — verified explicitly for representative data volume in §10.

## 9. "Most saved" is a foundation, not a feature

`sort=most_saved` needs a `Design.save_count` column to sort by, so this phase adds it (mirroring `view_count`/`like_count`'s denormalized-counter pattern) — but no "save a design to a collection" endpoint exists yet (Phase 2's `collections`/`collection_items` tables aren't wired to an API). The column exists purely as a sort-key foundation; it stays `0` until a future phase adds the feature that increments it.

## 10. Query and performance tests

`apps/api/tests/search/` covers:

- `test_search.py` — keyword matching (title and description), no-keyword-returns-all, empty results, every filter axis (category AND/OR semantics, artist, premium, difficulty, body placement), every sort mode, clear-filters behavior, cursor pagination correctness (no dupes/misses across a full walk), input validation (bad sort/difficulty/body_placement/too many categories/malformed cursor/cursor-from-a-different-sort), sanitization (control characters + truncation), and that a search records a `SearchEvent`.
- `test_suggestions.py` — prefix matching across all three suggestion types, the minimum-length gate, and that only published designs suggest.
- `test_history.py` — recent-searches ordering/dedup, that filter-only searches don't appear in history, per-user scoping, and clearing.
- `test_search_performance.py` — bulk-inserts 15,000 designs with a 200+ word shared vocabulary (chosen so keyword-match selectivity is realistic — a handful of percent, not most of the table, which is what actually makes the query planner reach for the GIN index instead of a sequential scan; verified empirically that a small, low-cardinality vocabulary makes Postgres correctly *prefer* a seq scan instead, which would be the wrong thing to assert against). Asserts via `EXPLAIN` that the GIN index is actually used (not just present), and that the search/suggestions/pagination endpoints stay within a generous latency budget at that scale.

## 11. Web and Flutter clients

Both clients follow the same shape as Phase 7's gallery views (own loading/error/empty state per section, no shared data-fetching library):

- **Web** (`src/components/search/search-view.tsx` + `/search` page): search input with debounced suggestions dropdown, a filter panel (category checkboxes grouped by axis, price radio, sort select), recent-searches chips, results grid + "Load more", and an empty state whose action button is "Clear filters" when any filter is active. Three new BFF proxy routes (`/api/designs/search`, `/search/suggestions`, `/search/history`) follow the exact pattern of Phase 7's `/api/designs` route — except they deliberately do **not** pass through a `Cache-Control` header: every search records a `SearchEvent` server-side, and a cached response would silently suppress that logging for a repeated identical query.
- **Flutter** (`lib/features/search/search_screen.dart`, reached via a search icon on the Discover tab's app bar, pushed as `/search`): same data model, filters presented as a modal bottom sheet (the idiomatic mobile pattern, vs. the web's always-visible sidebar) rather than a fixed panel.

Selecting a suggestion behaves differently by type: a "design" suggestion navigates straight to it; "category" and "artist" suggestions apply as filters instead (there's no single result to jump to for either), which is also how an artist filter gets set at all — neither client has a standalone artist directory/picker to build one from scratch, so the suggestions endpoint doubles as the only entry point into artist filtering.

## 12. What Phase 8 deliberately does not do

Per the phase brief: PostgreSQL full-text search only — no Typesense/Meilisearch yet (the provider abstraction in §1 exists specifically so that migration doesn't require a route-layer rewrite later). No fuzzy/typo-tolerant or per-word-prefix suggestions (see §6). No "save to collection" feature behind `sort=most_saved` (see §9). No client-side caching of search results (the same reasoning as the web `Cache-Control` decision in §11 — every search needs to reach the backend to be logged).

## 13. Related documents

- [design-gallery.md](design-gallery.md) — the Phase 7 gallery backend/clients this phase builds on (cursor pagination, `DesignSummaryOut`, client-state conventions)
- [design-catalog.md](design-catalog.md) — the Phase 6 category taxonomy (`category_type` axes) this phase's filters query
- [migration-guidelines.md](migration-guidelines.md) — the backfill-before-tightening-a-constraint pattern this phase's migration follows for `search_vector`/`save_count`
