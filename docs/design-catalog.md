# MehndiVerse — Design Catalog Backend (Phase 6)

Status: Draft (Phase 6)
Last updated: 2026-07-14

This document covers the category taxonomy, design records, and image upload pipeline introduced in Phase 6. It is backend-only — no gallery/browsing UI is built yet in any client app (see [feature-scope.md](feature-scope.md)).

## 1. Category taxonomy

`categories` (Phase 2) gained a `category_type` column (Phase 6), a CHECK-constrained enum with six values: `style`, `occasion`, `body_part`, `difficulty`, `density`, `region`. A single table holds every axis rather than six separate tables, so `design_categories` stays one many-to-many join regardless of how many axes a design is tagged across.

This is deliberately independent of `designs.difficulty_level` / `designs.body_placement` (direct columns from Phase 2): those are hard, single-valued filterable attributes; the category taxonomy is a browsable, multi-valued tagging system. A design can have a `difficulty_level` of `advanced` *and* be tagged with the `difficulty` category "Advanced" for discovery purposes — they aren't required to agree, and nothing enforces that they do in this phase.

Ten categories were seeded in Phase 2 (style/occasion/body_part, unlabeled at the time); Phase 6's migration backfills their `category_type` and seeds ten more across `difficulty`, `density`, and `region` so all six axes have at least a few real rows.

Managed via `GET /categories` (public read, optional `category_type` filter) and `POST`/`PATCH /categories` (admin/super_admin only — see `app/api/routes/categories.py`).

## 2. Design records and lifecycle

`status` (Phase 2: `draft` / `published` / `archived` / `flagged`) is a single column doing double duty as **both** publishing status and moderation state — a `flagged` design is implicitly unpublished, rather than tracked on a separate axis. This was a deliberate simplification for Phase 6: there is no moderation *action* endpoint yet (no way to flag/unflag through the API), so a second dimension would have nothing to write to it. A later moderation phase can either keep using this column or split it out; either way, `list_published_designs`/`get_design` only special-case `published`, so nothing here assumes `flagged` is unreachable.

Two other flags:
- `is_featured` (Phase 2, unused until now) — platform-curated promotion.
- `is_premium` (Phase 6) — marks a design as gated/paid content. No access enforcement exists yet; this phase only stores and exposes the flag.

### Publishing lifecycle

Owners (or staff) move a design between `draft` and `published` via `PATCH /designs/{id}` — validated against `DESIGN_OWNER_STATUS_TRANSITIONS` in `app/db/enums.py`, the same "transition table as source of truth" pattern Phase 2 used for bookings. `archived` and `flagged` are **not** reachable through this endpoint's `status` field at all (rejected at the Pydantic layer, see `DesignUpdateRequest._validate_status`):

- Archiving is a dedicated `POST /designs/{id}/archive` action — one-way in this phase (no unarchive endpoint).
- Flagging has no endpoint yet (see above).

## 3. Ownership and permissions

A design is "owned" by whoever's `artist_profile_id` it carries — resolved via `ArtistProfile.user_id`, not a separate ownership column. `artist_profile_id = NULL` means platform-curated (created by staff, editable only by staff).

Three permission tiers, all computed per-request from the validated token's effective role (never trusted from the client):

| Action | Who |
|---|---|
| Create a design | The design's own artist (`artist`/`verified_artist`) or `admin`/`super_admin` |
| View a non-published design | Its owner, or `moderator`/`admin`/`super_admin` |
| Edit / archive / upload images | Its owner, or `admin`/`super_admin` (not `moderator` — moderators review, they don't edit content) |

An artist with the `artist` role but no `ArtistProfile` row yet gets a 422 on create ("You need an artist profile before creating designs.") rather than a confusing 403 or a design nobody can find — artist-profile self-service creation is a later phase's job.

## 4. Image upload pipeline

`POST /designs/{id}/images/*` implements the eight-step pipeline end to end:

1. **Request upload authorization** — `POST /designs/{id}/images/authorize` creates a `DesignImage` row in `pending` status and returns an `image_id` plus the size/type constraints the client must honor.
2. **Validate file type and size** — on the follow-up upload call, the declared `Content-Type` is checked first (fast reject), then the actual bytes are decoded with Pillow (authoritative — see `app/core/images.py`, shared with the Phase 5 avatar pipeline).
3. **Upload to object storage** — the validated, metadata-stripped original is uploaded to the `portfolio` Supabase Storage bucket (the bucket Phase 3 reserved for artist portfolio content — see `infrastructure/supabase/storage_policies.sql`) via the service-role-authenticated `app/integrations/supabase_storage.py`, never exposing storage credentials to any client.
4. **Record the upload** — `storage_path`, `mime_type`, `file_size_bytes`, `checksum_sha256`, `original_filename`, `uploaded_by`, and the decoded `width`/`height` are written to the row immediately after the original uploads successfully.
5. **Queue image processing** — `app/services/design_image_processing.py::queue_image_processing()` is the named function boundary for this step. Phase 6 has no background worker (Celery/RQ/etc.) provisioned, so it runs **synchronously in-request** right now; a later phase can replace its body with "publish a job and return" without changing the function's contract or the status state machine below.
6. **Generate thumbnail variants** — two variants, `small` (≤200px) and `medium` (≤800px), generated from the already-validated original via `generate_thumbnail()` and uploaded alongside it.
7. **Store dimensions and metadata** — width/height were already captured at step 4; thumbnail URLs are added once they exist.
8. **Mark ready only after processing** — the row only reaches `status = ready` once both thumbnails have uploaded successfully. Any storage failure along the way marks it `failed` with `processing_error` set, rather than leaving it stuck in `processing` or raising a 500 to the client (the upload endpoint still returns 200 with the failed state — the client can inspect `status` and retry a fresh authorize/upload cycle).

Only `ready` images are ever returned from `GET /designs/{id}` or `GET /designs/published` to non-owner/non-staff callers — `pending`/`processing`/`failed` rows stay visible to the owner and staff only.

## 5. Public-facing endpoints

`GET /designs/published` and `GET /designs/{id}` still require authentication, consistent with every other endpoint in the backend so far — there is no anonymous API surface anywhere yet. Building a truly public, anonymous-friendly browsing surface (with its own rate-limiting/abuse considerations) is explicitly deferred; per this phase's brief, **the complete customer gallery is not being built yet**, so this is a foundation, not the final discovery experience.

## 6. Related documents

- [database-schema.md](database-schema.md)
- [booking-status-rules.md](booking-status-rules.md) — the sibling transition-table pattern this phase reuses
- [profile-and-privacy.md](profile-and-privacy.md) — the sibling secure-upload pattern this phase reuses
