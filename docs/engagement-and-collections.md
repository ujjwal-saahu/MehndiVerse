# MehndiVerse — Likes, Saves, and Collections (Phase 9)

Status: Draft (Phase 9)
Last updated: 2026-07-16

This document covers likes, quick-saves, and user-curated collections — introduced in Phase 9 on top of the gallery (Phase 7) and search (Phase 8) backends. The underlying `likes`/`collections`/`collection_items` tables were created back in Phase 2; this phase wires them up to real endpoints and clients for the first time.

## 1. Likes vs. saves vs. collection items

Three related but distinct concepts, all backed by the same two Phase-2 tables:

- **Like** (`likes` table) — a pure engagement signal. `POST/DELETE /designs/{id}/like`. No collection involved.
- **Save** (quick-save) — a one-tap bookmark. Under the hood, it's a `CollectionItem` in the current user's **default** collection (`Collection.is_default = true`, named "Saved Designs"), lazily get-or-created on first save (`get_or_create_default_collection` in `app/services/engagement.py`). `POST/DELETE /designs/{id}/save`.
- **Add to collection** — the full collection-management action: adding a design to any *named* collection the user owns, including (but not limited to) their default one. `POST /collections/{id}/items`.

"Save" is really "add to collection X (my default collection)" — both paths share the same `add_item_to_collection`/`remove_item_from_collection` service functions, so `save_count` (see §3) increments identically regardless of which endpoint a design entered the default collection through.

## 2. Atomicity and duplicate prevention

Likes, saves, and collection-item adds all follow the same pattern (`app/services/engagement.py`): attempt an `INSERT`, and treat a unique-constraint conflict as "already done" rather than erroring:

```python
try:
    with db.begin_nested():
        db.add(Like(user_id=user_id, design_id=design_id))
        db.flush()
except IntegrityError:
    return  # already liked — idempotent no-op
```

The database's unique constraint (`uq_likes_user_design`, `uq_collection_items_collection_design`) is the single source of truth for "does this already exist" — there's no separate `SELECT`-then-`INSERT` check, which would leave a race window between the check and the insert. Two concurrent identical requests can never double-insert or double-count: whichever one loses the race just observes the conflict and returns the same result as the winner. Each attempt runs inside a `SAVEPOINT` (`db.begin_nested()`) so a losing attempt's failed `INSERT` doesn't poison the rest of the request's transaction.

Unlike/remove-item are symmetric: a `DELETE ... WHERE user_id = ... AND design_id = ...` either affects one row (decrement the counter) or zero (no-op) — checked via `result.rowcount`, never a separate existence check first.

This same pattern protects the get-or-create-default-collection path: if two "save" requests race to create a user's first default collection, one succeeds and the other's insert conflicts against the partial unique index `uq_collections_one_default_per_user` (`ON collections (user_id) WHERE is_default`); the loser re-queries and returns the winner's row rather than erroring or creating a duplicate.

Verified with genuine cross-connection concurrency tests (`tests/engagement/test_concurrency.py`) — not just sequential calls in one transaction — using `ThreadPoolExecutor` with independent `Session`s against committed rows, for likes, default-collection creation, and adding to a named collection.

## 3. Atomic counter updates

`Design.like_count` and `Design.save_count` are denormalized counters (mirroring `view_count` from Phase 7), updated via a single `UPDATE designs SET like_count = like_count + 1 WHERE id = :id` — never a Python read-modify-write, so concurrent likes never lose an increment. Decrements are guarded (`WHERE ... AND like_count > 0`) as defensive belt-and-suspenders against ever going negative, on top of the DB `CHECK (like_count >= 0)` constraint from Phase 2/8.

## 4. Authorization

Mirrors the 404-vs-403 visibility-leak precedent established in `designs.py` (Phase 6/7):

- **Read** a collection (`GET /collections/{id}`, `GET /collections/{id}/items`): the owner can always see it; a non-owner gets it only if `is_private = false`, otherwise **404** — so a stranger can't distinguish "exists but private" from "doesn't exist."
- **Write** a collection (rename, delete, privacy/cover change, add/remove/reorder items): **403** for a non-owner, regardless of the collection's privacy — its existence is a much weaker leak than its content, and only the owner may ever mutate it. This exactly mirrors `designs.py`'s `_require_edit_permission` (403) vs. `_require_visible` (404) split.
- Liking/saving a design requires it be `published` — an unpublished design's id isn't a valid like/save target for a stranger (**404**); mirrors the visibility gate used for viewing.

Permission tests cover both directions for every collection mutation and read endpoint (`tests/collections/test_collections_crud.py`, `test_collection_items.py`).

## 5. Public vs. private collections and sharing

`Collection.is_private` (default `true`, from Phase 2) is now wired to real behavior: a public collection's detail (`/collections/{id}` on web, `/collections/:id` pushed route on Flutter) is a stable, shareable URL any logged-in user can view — the same "shareable but still requires login" treatment Phase 7 gave `/designs/{id}` (see docs/design-gallery.md#shareable-design-urls; true anonymous sharing remains out of scope for the same reasons). The user's default "Saved Designs" collection can be made public too, but can never be deleted (`400` on `DELETE` if `is_default`).

## 6. Collection cover

`Collection.cover_design_id` (nullable FK to `designs`, `ON DELETE SET NULL`) is an explicit pick — `PATCH /collections/{id}` with `cover_design_id`. When unset (or the picked design was deleted), the cover falls back to the most-recently-added item's design, resolved in one batched query per page of collections (`resolve_cover_urls` in `app/services/engagement.py`) rather than N+1.

## 7. Reordering collection items

`CollectionItem.sort_order` (new in this phase) persists manual drag-order within a collection. `PUT /collections/{id}/items/reorder` takes an ordered list of design ids and requires it to name **every** item currently in the collection, exactly once — a partial reorder is rejected (`422`) rather than guessed at, since the positions of unmentioned items would otherwise be ambiguous. Both clients therefore fetch a collection's full item list (capped at 100) before allowing reorder, and disable the reorder controls if there's more to load via "Load more" — reordering only a loaded subset would fail against the backend's full-list validation.

## 8. Optimistic UI with rollback

Both web (`components/gallery/like-save-buttons.tsx`) and Flutter (`features/engagement/engagement_widgets.dart`) flip a like/save button's state and count **immediately** on tap, before the backend call resolves, then reconcile with the server's actual response on success — or roll back to the exact pre-tap state (and surface an inline error) if the call fails:

```
tap → optimistic flip (isLiked, count±1) → await backend
  success → reconcile with server's authoritative {liked, like_count}
  failure → roll back to the captured pre-tap {isLiked, count} + show error
```

The same pattern covers collection-item removal and reordering on the web's collection-detail view (`components/collections/collection-detail-view.tsx`) and Flutter's `CollectionDetailScreen`: the item list updates immediately, then reverts if the backend call fails.

## 9. Saved-design screen

`GET /designs/saved` returns the current user's default collection's contents as ordinary `DesignSummaryOut`s, cursor-paginated by `added_at DESC` (most recently saved first) — a dedicated convenience endpoint so clients don't need to first resolve the default collection's id via `GET /collections`. Web: `/saved` page. Flutter: `/saved` pushed route, reached via a bookmark icon on the Discover tab's app bar (alongside Phase 8's search icon).

## 10. Pagination

Every list endpoint (`GET /collections`, `GET /collections/{id}/items`, `GET /designs/saved`) reuses the Phase 7/8 keyset-pagination cursor (`app/core/pagination.py`) — `collections` sorted by `created_at DESC`, items by `sort_order ASC` (the manual collection order), saved designs by `added_at DESC`. Same opaque-cursor, sort-tagged-and-rejected-if-mismatched contract as every other paginated endpoint in the app.

## 11. Query, permission, and concurrency tests

- `tests/engagement/test_likes.py`, `test_saves.py` — duplicate-prevention (double-like/double-save don't double-count), idempotent unlike/unsave, per-design like/save state on the design-detail response, 404s for unpublished/nonexistent designs, saved-designs screen pagination/ordering/empty-state.
- `tests/engagement/test_concurrency.py` — genuine cross-connection races (see §2).
- `tests/collections/test_collections_crud.py` — CRUD, duplicate-name rejection (409), rename/privacy-toggle/cover-pick, default-collection delete protection, 404-vs-403 visibility rules, cover resolution (explicit pick + most-recent-item fallback).
- `tests/collections/test_collection_items.py` — add/remove/duplicate-prevention, ownership enforcement, pagination, reorder (success, partial-list rejection, unknown-id rejection, ownership), and that adding to the default collection specifically increments `save_count`.

## 12. What Phase 9 deliberately does not do

No design-card-level like state on grid/search-result listings (`DesignSummaryOut` now carries `like_count`/`save_count`, but not per-viewer `is_liked` — computing that for a whole page of cards would mean extending the batched-summary machinery from Phases 7/8 across every existing call site; `is_liked`/`is_saved` are only computed for the single-design detail view, where the primary like/save UI lives). No explicit "clear collection cover" action in either client UI (the API supports sending `cover_design_id: null`, but neither client's UI exposes it — only picking a specific cover). No collection sharing beyond a stable, login-gated URL (no share sheets, no anonymous public links, no artist-role collections — the collections/saved-designs routes inherit the same customer-shell-only navigation Phase 8's search screen has on Flutter).

## 13. Related documents

- [design-gallery.md](design-gallery.md) — the Phase 7 gallery backend (`DesignSummaryOut`, cursor pagination, 404-vs-403 visibility precedent) this phase builds on
- [design-search.md](design-search.md) — the Phase 8 search backend whose `DesignSummaryOut`/pagination conventions this phase reuses
- [migration-guidelines.md](migration-guidelines.md) — the backfill-before-tightening-a-constraint pattern this phase's migration follows
