# Hand/foot design preview

Phase 19. A basic, non-AR "try it on" tool: upload a hand or foot photo,
overlay a transparent mehndi design on it, and move/resize/rotate/flip/
adjust its opacity before saving, exporting, sharing, or sending the result
to a booked artist. No landmark detection or AR placement — the user
positions the overlay by hand.

## 1. Do not upload private photos unless required

The photo never reaches the backend just because the user is editing.
Photo selection, and every move/resize/rotate/flip/opacity/reset action,
happens **entirely client-side** — in the browser via CSS transforms +
Canvas (`apps/web/src/components/preview/overlay-editor.tsx`) or in Flutter
via `Transform`/`GestureDetector` (`apps/mobile/lib/features/previews/
preview_studio_screen.dart`). The photo is only ever uploaded when the user
explicitly:

- **Saves** the project (`POST`/`PATCH /previews`) — the first point any
  photo bytes leave the device.
- **Exports** with an existing saved project (the composited image is also
  persisted server-side so Share/Send-to-artist have something to point
  at).

Every client surface shows a storage-behavior banner before/around the
photo picker explaining this explicitly (§2).

## 2. Explaining storage behavior to users

Both clients render the same message near the photo picker: the photo
stays on-device while editing; saving uploads it to secure, private
storage that only the owner (and any artist they explicitly send it to)
can read; and the user can delete the project — and its stored photo — at
any time. This isn't just a UI courtesy; it's a direct requirement from the
product spec, and it's the honest description of §1/§6's actual behavior,
not aspirational copy.

## 3. Editable preview state

`PreviewProject` (`app/db/models/ai.py`, Phase 2 schema, first given routes
this phase) stores:

- `source_storage_path` / `result_storage_path` — bucket-relative paths
  (never URLs — see §6).
- `source_width` / `source_height` — so a client resuming an edit doesn't
  need to re-measure the photo.
- `overlay_transform` (JSONB) — `{x, y, scale, rotation_degrees,
  flip_horizontal, opacity}`. `x`/`y` are **fractions (0..1)** of the
  photo's width/height, not pixels, so the same transform renders
  identically regardless of what resolution/screen the photo is displayed
  at. `scale: 1` means the overlay's width is 40% of the photo's width
  (`BASE_OVERLAY_WIDTH_FRACTION`, kept identical across web and mobile) —
  an arbitrary but reasonable default sticker size the user then adjusts.
- `shared_with_booking_id` — set by "send to artist" (§8).

"Layer reset" has no dedicated endpoint — it's just the client resetting
its local transform state back to `{x: 0.5, y: 0.5, scale: 1,
rotation_degrees: 0, flip_horizontal: false, opacity: 1}` before the next
save, exactly like every other edit.

## 4. Upload validation

`app/core/images.py::process_preview_photo_upload` — reuses the same
Pillow re-encode pipeline every image upload in this codebase goes through
(design photos, avatars): rejects anything Pillow can't decode as JPEG/
PNG/WEBP regardless of the claimed `Content-Type`, enforces a 15 MB size
cap (`MAX_PREVIEW_IMAGE_BYTES` — phone camera photos run larger than
portfolio marketing images), and additionally enforces a 24-megapixel
resolution cap (`MAX_PREVIEW_IMAGE_PIXELS`) as a decompression-bomb
safeguard specific to this phase's synchronous, request-path re-encoding
(see §5).

## 5. Memory and performance safeguards

- **Client-side downscaling before anything else.** The moment a photo is
  picked, both clients downscale it to at most 1600px on its longest side
  before it's ever held in editor state, drawn to a canvas, or uploaded —
  `apps/web/src/lib/image-utils.ts::downscaleImageFile` (an offscreen
  canvas re-encode) and Flutter's `ImagePicker(maxWidth/maxHeight/
  imageQuality)` (downscaling done by the platform picker itself, before
  the bytes ever reach Dart). A 12MP phone photo never sits in memory at
  full resolution during editing on either platform.
- **Server-side resolution cap** (§4) as defense-in-depth against a small
  file that decodes to an enormous pixel buffer, on top of Pillow's own
  default `Image.MAX_IMAGE_PIXELS` guard.
- **Rate limiting**: the image-processing-heavy endpoints (create/update/
  export) are rate-limited (`preview_rate_limit`, default 20/minute);
  cheap reads/share/delete are not.
- **Compositing captures on-screen resolution, not necessarily the
  source's full resolution** — both `exportComposite()` (web canvas) and
  `_captureComposite()` (Flutter `RenderRepaintBoundary.toImage`) render
  from what's already on screen rather than re-rendering an off-screen
  tree at full photo resolution. This is a deliberate simplicity/memory
  trade-off appropriate for a "basic" phase; a higher-fidelity export is a
  natural follow-up, not a correctness bug.

## 6. Secure stored preview images

Hand/foot photos are real photos of a customer, not marketing content —
they get the same private-bucket treatment `verification-documents`
already has (docs/artist-verification.md#document-privacy), not
`portfolio`'s public-read treatment:

- New private Supabase Storage bucket `preview-projects`
  (`infrastructure/supabase/storage_policies.sql`), owner-only at the
  storage-policy level.
- `PreviewProject.source_storage_path`/`result_storage_path` store
  bucket-relative paths, never durable URLs.
- Every response mints a **fresh signed URL** at read time
  (`app/services/previews.py::get_signed_source_url`/
  `get_signed_result_url`, 10-minute TTL) — nothing durable is ever handed
  to a client. "Share" mints a separate, slightly longer-lived (1 hour)
  signed URL, reflecting the more deliberate, longer-lived intent behind
  an explicit share action, while still never being a permanent link.
- Deleting a project (§9) also best-effort deletes the underlying storage
  objects (`app/integrations/supabase_storage.py::delete_object`) — the
  database row's soft-delete is the authoritative "this is gone" signal;
  a storage cleanup failure never blocks the delete itself.

## 7. Export

Compositing (drawing the transparent design overlay onto the photo at the
user's chosen position/scale/rotation/flip/opacity) happens **entirely
client-side** — the backend never rasterizes anything. `POST /previews/
{id}/export` just validates and stores the already-flattened bytes a
client sends, through the exact same validation pipeline as the source
photo (§4). Both clients also offer a local-only save (browser download /
an in-app preview dialog) that works even for an unsaved project, since
compositing never required uploading anything.

## 8. Premium designs and entitlements

Selecting a premium (`Design.is_premium`) design for a preview reuses
Phase 18's entitlement check (`app/services/entitlements.py::
get_effective_features`) — a free-tier user gets a 403 exactly as they
would viewing that design's full images, so the preview feature can't be
used to route around premium-design gating.

## 9. Send to artist

`POST /previews/{id}/send-to-artist {booking_id}` requires the caller to
be both the preview's owner and the booking's customer, and reuses
`app/services/messaging.py::get_or_create_booking_conversation`/
`send_message` — the same booking-messaging infrastructure Phase 14 built,
not a parallel one. It does two things:

1. Sets `PreviewProject.shared_with_booking_id`, which
   `app/services/previews.py::require_viewable` checks — this is what lets
   the booking's artist view the preview at all (`GET /previews/{id}`);
   nobody else can, even with the id.
2. Posts a plain-text message in that booking's conversation announcing
   the share. It deliberately does **not** put a raw attachment URL in
   `Message.attachment_url` — that column persists a plain string forever,
   but every preview image URL is a short-lived signed URL (§6); baking one
   into a chat message would go stale within minutes. The artist instead
   opens the preview through the same authenticated `GET /previews/{id}`
   everyone else uses, which mints a fresh signed URL on every read.

## 10. Delete preview project

`DELETE /previews/{id}` — owner-only, soft-deletes the row
(`PreviewProject` has `SoftDeleteMixin`) and best-effort deletes both
storage objects (§6). A deleted project's id immediately 404s for every
viewer, including an artist it was shared with.

## 11. Loading and failure states

Every action (save, export, share, send-to-artist, delete) on both clients
has its own independent loading flag and error message — a failed export
doesn't block or clear an in-progress save, and vice versa. Photo/design
selection has its own validation-error slot separate from the save-time
error, so a rejected file type is shown immediately rather than only after
attempting to save.

## 12. CORS dependency (web)

Compositing on canvas (`overlay-editor.tsx::exportComposite`) loads the
design overlay image (and, when reopening a saved project, the source
photo's signed URL) with `crossOrigin="anonymous"`, then reads the
composited pixels back out via `canvas.toBlob()`. This only works if the
Supabase Storage buckets serving those images send permissive CORS
headers; a bucket that doesn't will make `toBlob()` throw (a "tainted
canvas" `SecurityError`) even though the on-screen CSS preview still works
fine. Flutter's `RenderRepaintBoundary.toImage()` capture has no such
restriction — it isn't a web canvas.

## 13. What Phase 19 deliberately does not do

- No AR/landmark detection — the user positions the overlay manually
  (explicitly out of scope per the phase request).
- No real recurring/native sharing integration — "Share" surfaces a
  signed URL via the Web Share API (with a clipboard-copy fallback) on
  web, and a copyable-link dialog on Flutter, since no share-sheet package
  exists in the Flutter app yet (the same gap Phase 18 documented for
  downloading a design — see docs/subscriptions-and-entitlements.md#client-
  implementations).
- No off-screen full-resolution export render (§5) — export captures
  on-screen resolution.
- No staff-facing moderation/management surface for preview projects —
  this phase is entirely customer/artist self-service.
