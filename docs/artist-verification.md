# MehndiVerse — Artist Onboarding and Verification (Phase 10)

Status: Draft (Phase 10)
Last updated: 2026-07-17

This document covers artist onboarding and the staff-side verification lifecycle — introduced in Phase 10 on top of the artist profile scaffolding created in Phase 2/4. Prior to this phase, `ArtistProfile.verification_status` had 5 values with no wizard, no document upload, and no admin review surface; this phase adds all of that plus a full audit trail.

## 1. Verification lifecycle

`ArtistVerificationStatus` (`app/db/enums.py`) has 7 values, replacing the old 5-value set (`pending/under_review/verified/rejected/suspended`):

```
draft → submitted → under_review → approved
                  ↘ more_information_required ↗
                  ↘ rejected
             approved ⇄ suspended
```

Two separate transition tables enforce who can move a profile between which states (`ARTIST_VERIFICATION_SELF_TRANSITIONS` / `ARTIST_VERIFICATION_STAFF_TRANSITIONS`, pure dict-of-frozensets validators, no DB access — mirrors the pre-existing `BOOKING_STATUS_TRANSITIONS` pattern):

- **Self (artist)**: `draft`/`rejected`/`more_information_required` → `submitted` only. An artist can never set their own status to anything else, including `approved`.
- **Staff**: `submitted` → `under_review`; `under_review` → `approved`/`rejected`/`more_information_required`; `approved` ⇄ `suspended`.

`ARTIST_PROFILE_EDITABLE_STATUSES = {draft, rejected, more_information_required}` — the only statuses in which `PATCH /artist/profile` and document upload are allowed. `is_editable` on `ArtistProfileOut` is computed from this set (and is always `false` on the staff-facing view, even if it would otherwise be true — editability is an owner-only concept).

`ArtistProfile.rejection_reason` is reused for both `rejected` and `suspended` outcomes (documented in code); `more_info_request` is dedicated to `more_information_required`. Both are cleared whenever a transition lands somewhere else, so a stale reason never lingers into a new review cycle.

`get_effective_role()` (`app/core/authz.py`) only grants the derived `verified_artist` effective role when `verification_status == approved` — `submitted`/`under_review`/etc. still resolve to the plain `artist` role.

## 2. Lazy onboarding

Becoming an artist requires no separate "sign up as artist" flow: `GET /artist/profile` (`app/api/routes/artist_onboarding.py`) lazily creates a `draft` `ArtistProfile` and flips the caller's stored `role` from `customer` to `artist` on first call, the same lazy-provisioning idiom `get_current_user()` already uses for the `User` row itself. Both clients treat this endpoint as the "start/resume onboarding" action:

- Web: visiting `/artist/onboarding` triggers the GET server-side before rendering the wizard.
- Flutter: `ArtistOnboardingScreen.initState()` calls `fetchProfile()` on mount.

Staff accounts (`moderator`/`administrator`/`super_administrator`) are blocked from this endpoint (`403`) — an admin can review applications but can never accidentally create one for themselves.

## 3. Onboarding fields

`ArtistProfileUpdateRequest` (`app/schemas/artist.py`) accepts a partial update (`exclude_unset`, so omitted fields are left untouched — only fields the client actually sent, including explicit `null`, are applied):

professional name, business name, headline, biography, years of experience, country (2-letter ISO, normalized to uppercase), city, service areas (list), languages (list), contact email/phone, social links (`instagram`/`facebook`/`twitter`/`tiktok`/`youtube`/`pinterest`/`website`, each validated to start with `http(s)://`).

Profile/cover images are handled separately (`POST /artist/profile/image`, `POST /artist/profile/cover-image`) — these are public marketing images, not verification evidence, so they reuse the `portfolio` bucket's existing public-read/owner-write policy (provisioned back in Phase 3) rather than the private documents bucket. Both clients treat them as immediate-upload actions (like the pre-existing avatar upload), not part of the step's saved patch.

Required for submission (`app/services/artist_verification.py::missing_submission_requirements`): professional name, bio, years of experience, country, city, plus at least one non-rejected `id_proof` document. `ArtistProfileOut.missing_requirements` is exactly this list, computed server-side and driving both wizards' "Review" step — neither client re-derives readiness locally, so there's no risk of the UI and the server disagreeing about what's required.

## 4. Document privacy

**Verification documents (`ArtistDocument`) are never public.** `POST /artist/documents` stores bytes in the private `verification-documents` bucket via `upload_private_object()`, which returns nothing — only a bucket-relative `storage_path` is persisted on the row, never a URL. The bucket's RLS policy (provisioned in Phase 3, `infrastructure/supabase/storage_policies.sql`) restricts read access to the document's owner or `app_is_staff()`.

Documents accept JPEG/PNG/PDF (`app/core/documents.py`): images are re-encoded and stripped of metadata via the existing `app/core/images.py` pipeline; PDFs get magic-byte (`%PDF-`) and size validation only, since they can't be safely re-encoded the way images can.

`ArtistDocument` has no soft-delete and no update-in-place: a rejected or superseded document stays in the table forever as part of the verification audit trail. Re-uploading (e.g. after a rejection) simply creates a new row; `missing_submission_requirements` already ignores `rejected` documents when checking readiness, so a rejected upload doesn't block resubmission once a new one lands.

## 5. Short-lived signed URLs

Nothing ever hands out a raw `storage_path` or a durable URL for a private document. `artist_document_out()` (`app/services/artist_summaries.py`) mints a fresh signed URL via `create_signed_url()` (`app/integrations/supabase_storage.py`, `POST /object/sign/{bucket}/{path}`, 5-minute TTL) **on every single response** — `ArtistDocumentOut.view_url` is never cached, never persisted, and never the same value twice. Both the artist's own document list and the staff review view go through this exact same function, so self-view and staff-view can never drift in what they expose.

## 6. Preventing self-approval

Role-gating alone (`require_roles("admin", "super_admin")`) is insufficient, because a staff member can independently hold an `ArtistProfile` of their own (nothing stops an admin from also being an onboarding artist). Every admin action endpoint in `app/api/routes/admin_artist_verification.py` — start-review, approve, reject, request-more-information, suspend, and document review — calls `_require_not_self(profile, current)` first, which raises `403` if `profile.user_id == current.user.id`, independent of role. Verified explicitly in `tests/artist/test_admin_verification.py::test_admin_cannot_approve_their_own_application` (constructs an `ArtistProfile` owned by the acting admin and asserts every transition endpoint rejects it).

## 7. Audit log

Every verification action — submit, start-review, approve, reject, request-more-information, suspend, and document review — writes an `AuditLog` row (`app/services/audit.py::record_audit_log()`, using the pre-existing Phase 2 `AuditLog` model, which had zero writers before this phase). Each entry captures `actor_id`, `action` (e.g. `artist_verification.reject`, `artist_document.review`), `before_state`/`after_state` (JSONB — at minimum the status transition, plus the reason/message text where one was given), IP address, and user agent. Entries are immutable — no update, no soft-delete — and are written in the same transaction as the state change itself, so an audit entry and its corresponding mutation can never diverge. `GET /admin/artists/{id}/audit-log` (staff-only, cursor-paginated, newest first) is the only read path; there is no artist-facing audit view.

## 8. Admin verification queue

`GET /admin/artists` (`app/api/routes/admin_artist_verification.py`) lists applications, defaulting to `submitted`/`under_review` (an explicit `status_filter` query param can widen or narrow this), cursor-paginated FIFO by `submitted_at ASC` — the oldest unreviewed application surfaces first. Viewing the queue/detail/documents/audit-log is available to `moderator`/`admin`/`super_admin`; only `admin`/`super_admin` may actually act on an application (`_EDIT_ROLES`), mirroring the `_VIEW_STAFF_ROLES`/`_EDIT_STAFF_ROLES` split Phase 6/7 established for design moderation. A moderator can therefore triage and review evidence but must escalate the actual decision.

Both clients implement the same shape: a filterable list (web: pill filters; Flutter: not yet built — the admin queue is web-only in this phase, since there's no staff-facing shell in the mobile app) linking to a detail view with the profile, documents (with per-document approve/reject), the action buttons appropriate to the current status, a reason/message prompt for reject/suspend/request-more-info, and the audit log.

## 9. Client implementations

- **Web**: `/artist/onboarding` (6-step wizard: about you, location & services, contact & social, photos, documents, review) and `/artist/verification-status` (read-only status + document list + resubmit link when editable). Admin: `/admin/artists` (queue) and `/admin/artists/[id]` (review). All backend calls go through `src/app/api/artist/*` and `src/app/api/admin/artists/*` proxy routes (never directly from the browser), consistent with every other feature in this app.
- **Flutter**: `ArtistOnboardingScreen` (same 6 steps, per-step `PATCH` save) and `ArtistVerificationStatusScreen`, both pushed routes reachable from either navigation shell via a role-conditional entry point on `ProfileScreen` ("Become an artist" for a customer, "Artist verification status" for an artist). The router's shell-gating (customers confined to the customer shell, artists to the artist shell) explicitly exempts these two routes, since a customer must be able to reach `/artist/onboarding` to become an artist in the first place. Document/image capture uses `image_picker` (camera/gallery) rather than a file picker — the mobile app has no PDF-picker dependency yet, so ID documents are captured as photos; a PDF upload path can be added in a later phase if needed. There is no admin queue on Flutter in this phase — staff review is web-only.

## 10. Query and permission tests

- `tests/artist/test_verification_state_machine.py` — pure transition-table tests (self vs. staff, valid vs. invalid), no DB.
- `tests/artist/test_onboarding.py` — lazy-create + role promotion, idempotency, staff-blocked, field validation (country normalization, social-link platform/URL checks), submission-readiness gating, full submit flow, edit-while-submitted rejection, double-submit rejection, profile/cover image upload.
- `tests/artist/test_documents.py` — auth/ownership requirements, PDF and image upload, invalid document type, non-PDF/non-image rejection, PDF-magic-byte spoofing rejection, optional business-license type, listing, upload-after-submit rejection.
- `tests/artist/test_admin_verification.py` — queue role-gating and default filter, self-approval prevention, the full transition matrix (including invalid transitions), resubmission after rejection, an audit-log entry written for every transition, document review (approve/reject-requires-reason), and that a stranger cannot reach a private document's signed URL through the admin endpoints.

## 11. What Phase 10 deliberately does not do

No artist-facing audit view (staff-only, per §7). No admin verification queue on Flutter (web-only, per §8/§9) — there is no staff-facing navigation shell in the mobile app yet. No PDF capture on Flutter (image-only via `image_picker`, per §9). No explicit document-deletion endpoint — a superseding upload after rejection is the only path (per §4), matching the model's own no-soft-delete design. No re-verification cadence/expiry (`approved` artists don't automatically re-enter review after a time period) — out of scope for this phase.

## 12. Related documents

- [authentication.md](authentication.md) — effective-role derivation (`#1`), the `verified_artist` derived role this phase's `approved` status feeds
- [user-roles-and-permissions.md](user-roles-and-permissions.md) — the `_VIEW_STAFF_ROLES`/`_EDIT_STAFF_ROLES` split this phase's admin routes reuse
- [database-schema.md](database-schema.md) — the no-soft-delete convention `ArtistDocument` follows
- [migration-guidelines.md](migration-guidelines.md) — the constraint-naming (`op.f(...)`) convention this phase's migration follows
