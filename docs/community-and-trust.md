# MehndiVerse — Community and Trust (Phase 16)

Status: Implemented (Phase 16)
Last updated: 2026-07-16

Follow/unfollow already existed (Phase 11, `app/services/artist_directory.py`). This phase adds the rest of the social/trust surface that sits on top of designs and bookings — design comments and replies, artist reviews and rating aggregation, and a shared reporting/moderation-queue mechanism — plus retrofits blocking enforcement onto follow, which had none. Builds on schema that has existed since Phase 2 (`comments`, `reviews`, `reports`, `follows`, `user_blocks`) but had little to no service/route layer until now, the same "Phase-2 pre-scaffolding" pattern seen throughout this project.

## 1. Design comments and replies

`POST/GET /designs/{id}/comments` (`app/services/comments.py`, `app/api/routes/comments.py`). A comment can only be created against a `published` design (422 otherwise) — commenting on a draft/archived/flagged design makes no sense since only published designs are publicly visible at all.

Body is sanitized the same way message bodies are (Phase 14's `sanitize_message_body()` precedent): `sanitize_comment_body()` strips any HTML-tag-like sequence (`<[^>]*>`) at write time rather than storing HTML-escaped text, avoiding the double-escaping ambiguity of needing every future renderer to know the body is already escaped.

## 2. Comment replies are flat

A reply's `parent_comment_id` must reference a **top-level** comment (one whose own `parent_comment_id` is null) — replying to a reply is rejected with 422. This is a deliberate scope simplification: no arbitrarily deep comment trees, matching how this phase's `CommentOut` shape is "top-level comment + flat list of replies," not a recursive tree. A client never needs more than one round-trip to see a comment's replies.

Editing (`PATCH /comments/{id}`) and deleting (`DELETE /comments/{id}`) are owner-only (403 otherwise) for both top-level comments and replies.

## 3. Review a completed booking

`POST /bookings/{id}/reviews` (`app/services/reviews.py`). Three eligibility rules, all enforced in the service layer (not just the schema):

- Only the booking's **customer** may review it — the artist gets 403, and so does any third party.
- The booking must be `completed` (422 otherwise) — you can't review a booking that's still in progress or was cancelled.
- **One review per completed booking** — enforced twice: an application-level existence check (409) and a DB-level `UniqueConstraint("booking_id")` on `reviews` as the backstop against a race between two concurrent submit attempts.

Rating must be an integer 1–5, validated both at the schema level (`Field(ge=1, le=5)`) and the service level (defense in depth — the service function is also callable directly from tests/scripts that bypass the Pydantic layer).

## 4. Artist rating aggregation

`ArtistProfile.rating_average`/`rating_count` are **fully recomputed** from the `reviews` table (`SELECT AVG(rating), COUNT(*) WHERE artist_profile_id = X AND deleted_at IS NULL`) inside the same transaction as every review write (`recompute_artist_rating()`), rather than incrementally adjusted the way `follower_count`/`like_count` are elsewhere in this codebase.

This is a deliberate departure from this project's usual incremental-counter pattern. Rated aggregates are exactly the kind of value where a missed decrement or a double-counted edit silently drifts from the truth over time and nobody notices until a customer complains that the number looks wrong; a full recompute inside the write's own transaction can't drift, by construction, at the cost of a cheap `AVG()`/`COUNT()` over what is realistically a small per-artist row count. The explicit requirement "aggregated ratings must remain consistent" is read as a mandate for correctness-by-construction over micro-optimization.

## 5. Reports enter a moderation queue

One shared function, `app/services/reports.py::create_report()`, backs **every** report surface — design (`POST /designs/{id}/report`), comment (`POST /comments/{id}/report`), user (`POST /users/{id}/report`), and message (`POST /messages/{id}/report`, refactored this phase from its original Phase 14 inline `Report(...)` construction to call the shared function). Consolidating them means the two abuse-prevention rules below are enforced in exactly one place instead of separately per surface:

- **Self-report rejection**: a `USER`-type report where `reported_entity_id == reporter_id` is rejected with 422.
- **No duplicate open reports**: the same reporter can't have two simultaneously-`pending` reports against the same target. Enforced twice — an application-level check (409, so the caller gets a clean, specific message) and a DB-level partial unique index, `uq_reports_one_pending_per_reporter_and_target` (`UNIQUE (reporter_id, reported_entity_type, reported_entity_id) WHERE status = 'pending'`), as the race-condition backstop. The partial-index technique mirrors `uq_collections_one_default_per_user` (Phase 6). Once the earlier report is resolved or dismissed, the same reporter can open a new one against the same target — the constraint only ever blocks a *second concurrently-open* report.

Every report starts `pending` — there is no auto-resolution path. A staff moderation queue (`GET /admin/reports`, moderator/admin/super_admin) lists reports (cursor-paginated, filterable by `status`/`reported_entity_type`) with an `entity_snapshot` (see §6) attached per item; `POST /admin/reports/{id}/resolve` and `.../dismiss` (admin/super_admin only) close a report out with optional `resolution_notes`, mirroring the `_VIEW_STAFF_ROLES`/`_EDIT_STAFF_ROLES` split established by `admin_artist_verification.py` (Phase 10).

Resolving or dismissing a report is **deliberately record-keeping only** — it never auto-deletes a comment, auto-unpublishes a design, or auto-suspends a user. Staff take those actions through the existing dedicated surfaces (comment delete, `admin_users.py`, design moderation) after reviewing the report. Keeping "enter a moderation queue" separate from "and then something automatically happens" avoids this phase silently growing into a full auto-moderation system nobody asked for.

### 5a. Moderation evidence preservation

`entity_snapshot()` reads the reported entity's *current* state at read time, regardless of whether it has since been soft-deleted — this is the concrete mechanism behind "deleting comments must preserve moderation evidence." A user "deleting" their own comment only ever sets `Comment.deleted_at` (`SoftDeleteMixin`, never a hard delete); `entity_snapshot()` for a `COMMENT`-type report deliberately does not filter on `deleted_at`, so a staff member reviewing an open report can always see exactly what was reported (`body`, `design_id`, `is_deleted`) even after the author deletes it from their own view.

## 6. Blocked users cannot directly interact

`app/services/blocking.py::is_blocked_either_direction()` is the one shared check — extracted this phase from Phase 14's messaging-only inline version, since it's now consumed by three independent surfaces:

- **Following**: `follow_artist()` rejects with 403 if either party has blocked the other. Previously unenforced — following had zero blocking coverage before this phase.
- **Commenting**: `create_comment()` rejects with 403 if the commenter and the design's owning artist have blocked each other.
- **Reviewing**: `create_review()` rejects with 403 if the customer and artist have blocked each other.
- **Messaging** (Phase 14, unchanged behavior, now sharing the same implementation): sending a message still rejects with 409 under the same condition — the different status code there is a pre-existing Phase 14 choice, not something this phase changed.

Blocking is directional in storage (`UserBlock.blocker_id`/`blocked_id`) but the check is symmetric: it doesn't matter who blocked whom, direct interaction is refused either way.

## 7. Abuse prevention

- **Rate limiting**: comment creation is capped at `comment_rate_limit` (default `20/minute`); every report endpoint (design/comment/user/message) is capped at `report_rate_limit` (default `10/minute`) — same IP-keyed `slowapi` limiter used by auth/search/messaging/payments (`app/core/config.py`).
- **Duplicate-report guard**: see §5 — the partial unique index is as much an abuse-prevention control (stops someone from spamming ten reports against the same target to force attention) as it is a data-integrity one.
- **Self-report rejection**: see §5.
- **Blocked-user enforcement**: see §6 — prevents a blocked user from circumventing the block by following, commenting on, or reviewing the person who blocked them (or vice versa).
- **Authorization**: every mutating endpoint checks ownership/role server-side — editing/deleting a comment, reviewing a booking, and resolving/dismissing a report all reject a non-owner/non-staff caller before touching any row, never relying on the client to hide a button.

## 8. Client implementations

- **Web**: a `CommentsSection` on the design-detail page (list/create/reply/edit/delete own, report), a `ReviewsSection` plus rating summary on the artist public-profile page, a `BookingReviewForm` shown on a completed booking's detail page, `ReportButton` used for design/comment/user reporting (and the artist profile's "Report artist" action), and a staff-only moderation queue page (`/admin/reports`) with resolve/dismiss actions gated to admin/super_admin.
- **Flutter**: the same customer-facing surfaces — comments (with replies, edit/delete own, report) on the design-detail screen, a reviews list on the artist public-profile screen, a review-submission form on a completed booking's detail screen, and report actions for design/comment/user (message reporting already existed from Phase 14 and now shares the same reusable report-reason dialog). The staff moderation queue is **not** built for Flutter, consistent with this project's recurring "customer/artist-facing surfaces get parity across clients; staff tooling stays web-only" scope discipline (see [booking-messaging.md](booking-messaging.md#9)).

## 9. What Phase 16 deliberately does not do

No comment "likes" or nested reply threads beyond one level (§2). No automatic action on report resolution — resolving/dismissing is record-keeping only (§5). No artist response-to-review feature (the `Review.artist_response` column exists from Phase 2 but nothing writes to it yet — a future phase's concern). No un-following notification or "why was I unfollowed" surface. No appeal/dispute flow for a resolved report. No bulk moderation actions (one report resolved/dismissed at a time). No SMS or push notification when a report is filed or resolved — staff are expected to check the queue, the same way they check the artist-verification queue.

## 10. Related documents

- [booking-messaging.md](booking-messaging.md) — the message-reporting precedent this phase's shared `create_report()` now also backs, and the client-parity scope-discipline pattern §8 follows
- [artist-verification.md](artist-verification.md) — the staff RBAC (`_VIEW_STAFF_ROLES`/`_EDIT_STAFF_ROLES`) and cursor-paginated-queue pattern the moderation queue reuses
- [engagement-and-collections.md](engagement-and-collections.md) — the partial-unique-index technique (§5) and "insert, then treat a unique-constraint conflict as already-done" pattern behind follow/unfollow
- [artist-directory.md](artist-directory.md) — the pre-existing follow/unfollow/follower-count implementation this phase adds blocking enforcement to (§6)
- [profile-and-privacy.md](profile-and-privacy.md) — the `user_blocks` foundation §6 is the second consumer of
