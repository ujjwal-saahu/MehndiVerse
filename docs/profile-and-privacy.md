# MehndiVerse — Profiles, Preferences, and Privacy (Phase 5)

Status: Draft (Phase 5)
Last updated: 2026-07-14

This document covers the customer profile, preferences, and privacy/blocking foundation introduced in Phase 5, and the security decisions behind avatar uploads.

## 1. Resources

Four backend resources, all under `/api/v1/users` (see `app/api/routes/profile.py`):

| Resource | Endpoints | Notes |
|---|---|---|
| Profile | `GET/PATCH /users/me/profile`, `GET /users/{user_id}/profile` | Display name, avatar, bio, city/country, locale, timezone. |
| Avatar | `POST /users/me/avatar` | Multipart upload; see [§3](#3-avatar-uploads). |
| Preferences | `GET/PATCH /users/me/preferences` | Notification, marketing, and privacy settings — one resource, not three, per [§2](#2-why-preferences-is-one-resource). |
| Blocks | `GET/POST /users/me/blocks`, `DELETE /users/me/blocks/{user_id}` | Self-service block/unblock foundation; see [§4](#4-blocked-user-foundation). |

`PATCH` endpoints are true partial updates: a field is only changed if the client explicitly includes it in the request body (`exclude_unset=True` server-side). Omitting a field leaves it untouched; the API has no way to blank out `display_name`, `bio`, or `city` — they reject empty strings by validation, so "clearing" a field isn't supported in this phase.

## 2. Why preferences is one resource

The Phase 5 brief calls for "user preferences," "notification preferences," and "privacy preferences" as separate concerns. Rather than three overlapping endpoints, `user_preferences` is a single table/resource whose *fields* fall into those three categories:

- Notifications: `email_notifications`, `push_notifications`, `sms_notifications`
- Marketing: `marketing_opt_in`
- Privacy: `profile_visibility`, `show_location`, `allow_messages_from_strangers`

Every authenticated user gets a `user_preferences` row lazily (same pattern as `profiles` — see `_get_or_create_preferences` in `app/api/routes/profile.py`), so a token that's valid but was never routed through `/auth/register` (e.g. provisioned via `get_current_user`'s lazy path) still resolves to sane defaults.

## 3. Avatar uploads

`POST /users/me/avatar` is the only file-upload endpoint in the app so far. Every uploaded image goes through three steps before it's stored, all in `app/core/images.py`:

1. **Size check** — rejected above 5 MB (matches the `avatars` Supabase Storage bucket's `file_size_limit`, see `infrastructure/supabase/storage_policies.sql`) before any decoding happens.
2. **Type validation by content, not claim** — the file is opened and decoded with Pillow; the client's declared `Content-Type` is checked first as a fast reject, but the authoritative check is what Pillow actually decodes the bytes as. A `.png` claim wrapping arbitrary bytes fails here.
3. **Metadata stripping** — the decoded image is re-encoded and saved without an `exif=` argument, which drops EXIF/ICC/XMP blocks entirely (GPS coordinates, camera/device identifiers, etc.) rather than attempting to selectively remove known-sensitive tags. EXIF orientation is applied to the pixels first (`ImageOps.exif_transpose`) so the re-encoded image isn't sideways once the orientation tag is gone.

Only the re-encoded bytes are uploaded — via `app/integrations/supabase_storage.py`, a thin server-side client using the Supabase **service-role key** (never exposed to any client). This is what makes the upload "secure": the browser/app never talks to Storage directly, never sees a service-role credential, and the object that ends up in Storage is never the client's original bytes.

Web forwards the raw upload through `POST /api/profile/avatar` (a pass-through Route Handler, not `backendFetch()`, since it needs a fresh multipart boundary rather than the JSON content type `backendFetch()` forces). Flutter uploads via `ProfileRepository.uploadAvatar()` using Dio's `MultipartFile`. Both call the same backend endpoint and get the same server-side validation — there's no separate "web" or "mobile" validation path.

## 4. Blocked-user foundation

`user_blocks` (`blocker_id`, `blocked_id`) is a directed, self-service relationship — the same shape as `likes`/`follows` from Phase 2. A user can block/unblock/list only their *own* outgoing blocks; nothing here inspects or hides content elsewhere in the app yet. This is explicitly a **foundation**: messaging, discovery, and notifications don't consult `user_blocks` in Phase 5. Whichever later phase builds those features is responsible for checking it (see the model docstring in `app/db/models/user.py`).

## 5. Privacy enforcement

`GET /users/{user_id}/profile` is the one endpoint where privacy actually has teeth:

- If `profile_visibility` is `private` and the caller is neither the profile's owner nor staff (`moderator`/`admin`/`super_admin`), the response is **404**, not 403 — this avoids using the status code to confirm whether a given user id exists at all.
- If `show_location` is `false`, `city`/`country` are stripped from the response for anyone but the owner (staff still see them, for moderation purposes).
- The owner always sees their own full profile regardless of their own visibility/location settings.

**No user can edit another user's private profile** by construction, not by a permission check: every write endpoint (`PATCH /users/me/profile`, `PATCH /users/me/preferences`, `POST /users/me/avatar`) operates on `current.user.id` from the validated token — none of them accept a target user id. There is no request shape that edits someone else's data; a client attaching an extraneous `user_id` field to a request body is simply ignored (Pydantic drops unrecognized fields), which is covered by `test_update_profile_has_no_route_to_target_another_user` in `tests/profile/test_profile.py`.

## 6. Client architecture

- **Flutter**: `features/profile/` — `ProfileRepository` (Dio-based, mirrors `AuthRepository`'s pattern), plain hand-written model classes (no `freezed`/codegen — these are flat DTOs, not state unions, so the added build step wasn't worth it), and one screen per concern (`ProfileScreen`, `EditProfileScreen`, `SettingsScreen`, `LanguageSettingsScreen`, `NotificationPreferencesScreen`, `PrivacySettingsScreen`, `BlockedUsersScreen`). Profile/settings routes are ordinary `GoRoute`s pushed on top of whichever shell (customer or artist) is active, not `StatefulShellBranch`es, since they aren't bottom-nav tabs.
- **Web**: `/account` (profile view), `/account/edit`, `/account/settings`, `/account/settings/privacy` — all under the existing `(marketing)` route group and covered by the existing `/account/:path*` middleware gate. Route Handlers under `src/app/api/{profile,preferences,blocks}` are the only code that holds a raw access token or calls the backend directly, per the pattern established in Phase 3.

## 7. What Phase 5 deliberately does not do

- No enforcement of blocks in messaging/discovery/notifications (not built yet).
- No way to clear `bio`/`city`/`display_name` back to empty via the API (blank values are rejected, not treated as "unset").
- No public-profile browsing UI beyond the authorization semantics in `GET /users/{user_id}/profile` — there's no design-discovery surface yet for that endpoint to back.

## 8. Related documents

- [design-system.md](design-system.md)
- [authentication.md](authentication.md)
- [database-schema.md](database-schema.md)
