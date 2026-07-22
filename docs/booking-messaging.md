# MehndiVerse — Booking Messaging and Notifications (Phase 14)

Status: Implemented (Phase 14)
Last updated: 2026-07-26

Booking-scoped messaging and the notification system that surfaces booking events — see [booking-lifecycle.md](booking-lifecycle.md) for the booking state machine this phase hangs off of. Builds directly on schema that has existed since Phase 2 (`conversations`/`conversation_members`/`messages`, `notifications`) and Phase 5 (`user_blocks`, `user_preferences`, `user_devices`) but had nothing writing to it until now.

## 1. One conversation per booking

`Conversation.booking_id` is unique at the database level (Phase 14 migration) — Postgres treats multiple `NULL`s as distinct, so `inquiry`/`support` conversations (unused this phase) aren't affected, but a `booking` conversation can never accidentally duplicate. The conversation is created **lazily**, the first time either party opens or messages about a booking (`get_or_create_booking_conversation()`), not eagerly at booking-creation time — matching this codebase's established lazy-provisioning pattern (draft artist profiles, placeholder `User` rows). Creating one requires the booking to be past `draft` (422 otherwise): a draft is the customer's private scratch space, and the artist doesn't even know it exists yet (see [booking-lifecycle.md](booking-lifecycle.md#4)).

A race between both parties opening the conversation for the first time simultaneously is handled the same way as `get_or_create_default_collection` (Phase 6): the insert is wrapped in a `SAVEPOINT` (`db.begin_nested()`), and a losing `IntegrityError` against the unique constraint just re-fetches the winner.

## 2. Authorization

Every conversation-scoped endpoint resolves the underlying booking first and checks the caller is one of its two parties (`booking.customer_id` or the artist who owns it) — a third party gets **403**, mirroring `app/api/routes/bookings.py`'s identical check. This is deliberately duplicated (not imported) across `bookings.py` and `messaging.py`, matching this codebase's existing precedent of small per-route-file authorization helpers.

Staff (dispute-review) access is a **separate router** (`app/api/routes/admin_messaging.py`), not a bypass branch inside the member-facing one — see §7.

## 3. Notifications

`app/services/notifications.py::notify_user()` is the single fan-out point every other service calls. One logical event can produce multiple `Notification` rows — one per channel — because the Phase 2 schema already models `Notification.channel` as a single required field per row, giving a genuine per-channel delivery history rather than one channel-agnostic log entry:

- **In-app** is always written — there is no preference toggle to disable it (only email/push/sms have one, `UserPreference`, Phase 4/5).
- **Push** is written (and "dispatched" — see §4) only if `push_notifications` is enabled and the user has at least one active `UserDevice`.
- **Email** is written (and dispatched) only if `email_notifications` is enabled.
- SMS is out of scope this phase (no SMS foundation was requested).

### 3a. Notification preferences

Already fully built — `GET/PATCH /users/me/preferences` (Phase 4/5). This phase's contribution is that `notify_user()` finally *reads* those toggles instead of them being unused columns.

### 3b. Booking-request, quote, and status alerts

Each booking action in `app/services/booking.py` calls `notify_user()` (or the `_notify_other_party()` helper for actions either party can trigger) with an event-specific title/body, rather than a single generic hook bolted onto `transition_booking()`:

- `submit_booking()` → notifies the artist ("New booking request").
- `send_quote()` → notifies the customer ("You received a quote"/"Your quote was updated" for a revision).
- `accept_quote()` → notifies the artist ("Booking confirmed" — the message differs if a deposit is now due).
- `reject_quote()` → notifies the artist ("Quote declined").
- `cancel_booking()` / `request_reschedule()` → notify whichever party did **not** trigger the action, via `_notify_other_party()`.

A blanket auto-notify inside `transition_booking()` itself was deliberately rejected: it would either double up with these specific notifications (e.g. accepting a quote both sends "Booking confirmed" *and* a generic "status changed to confirmed") or force every transition into one generic, less useful message.

New messages also notify the recipient (`app/services/messaging.py::send_message()`), type `message`.

### 3c. Notification history (in-app inbox)

`GET /notifications` (cursor-paginated, `unread_only` filter), `GET /notifications/unread-count`, `POST /notifications/{id}/read`, `POST /notifications/read-all` — the read-side of everything `notify_user()` writes.

### 3d. Reminder foundation

`send_booking_reminders(db, within_hours=24)` finds occupying bookings (see [booking-lifecycle.md](booking-lifecycle.md#6)) whose date falls inside the window and notifies both parties. It is a **foundation**, not a running scheduler — nothing in this phase calls it automatically (no cron/task-queue infrastructure exists in this environment yet); a future phase's periodic job is expected to call it and track "already reminded" itself, since this function will happily notify again every time it's called for the same booking.

## 4. Push and email notification foundations

`app/integrations/push_notifications.py` and `app/integrations/email_notifications.py` are the two seams a future phase swaps a real provider into. Neither talks to a real push/email provider today (no FCM/APNs credentials, no SMTP provider configured in this environment) — both simply log the attempt (`push_notification_dispatched` / `notification_email_dispatched`) and mark the `Notification` row's `sent_at`. `UserDevice` (Phase 5's push-token registration) is finally read by the push path, even though nothing is actually pushed.

## 5. Content safety

**Attachments**: image messages reuse the exact `process_image_upload()` pipeline from booking inspiration images (Phase 13) — decode/re-validate/re-encode via Pillow (strips EXIF), same size cap, same public `portfolio` storage bucket. An attachment that isn't a genuinely decodable image is rejected with 422 regardless of its claimed content type.

**Escaping unsafe message content**: a message body is plain text only, no rich text or markdown. `sanitize_message_body()` strips any HTML-tag-like sequence (`<...>`) at write time, so the stored body is always exactly what a plain-text renderer should show — this avoids the double-escaping ambiguity of storing HTML-entity-escaped text and needing every future renderer to know not to escape it again. Web and Flutter both render message bodies as plain text (React's default JSX interpolation, Dart's `Text` widget) — neither uses `dangerouslySetInnerHTML` or an HTML `WebView`, so message content is never interpreted as markup on either client either. The other place user-generated text becomes real HTML is the email-notification foundation (§4): `render_email_body()` calls Python's `html.escape()` on any embedded excerpt at the point the HTML is actually constructed — the textbook-correct place for output encoding.

**Rate limiting**: `POST /bookings/{id}/conversation/messages` is rate-limited (`message_rate_limit`, default `20/minute`, same IP-keyed `slowapi` limiter as auth/search — see `app/core/config.py`).

**Blocking**: `is_blocked_either_direction()` checks `user_blocks` (Phase 5 foundation) before allowing a send — if either party has blocked the other, sending fails with 409. This is the first phase to actually enforce `user_blocks` anywhere, per that model's own docstring ("later phases that touch \[messaging] are responsible for checking it").

**Avoiding unnecessary contact-info exposure**: the conversation list/detail schemas (`ConversationSummaryOut`/`ConversationBookingContextOut`) deliberately mirror `BookingSummaryOut`, not `BookingDetailOut` — `contact_name`/`contact_email`/`contact_phone` never appear in any messaging response. A conversation only ever exposes the other party's *display name* (artist professional/business name, or customer profile display name), never raw account contact fields.

## 6. Pagination and read status

Messages paginate newest-first with an opaque cursor (`(created_at, id)` keyset, mirroring the `AuditLog`/design-gallery cursor pattern from earlier phases) — a page plus `has_more`/`next_cursor`.

Read status is a per-conversation-member cursor (`ConversationMember.last_read_at`, already in the Phase 2 schema), not a per-message read receipt table. A message's `is_read` in API responses is computed relative to its **recipient** (whichever member isn't its sender) — deliberately *not* relative to whoever happens to be asking, since "has the other person read this" is a property of the message itself, not of the viewer.

## 7. Admin access for dispute review

`GET /admin/bookings/{id}/conversation/messages` (staff roles: moderator/admin/super_admin) is a separate, read-only router from the member-facing one. Every view is recorded to `audit_logs` (`action="conversation.admin_view"`, reusing the Phase 10 audit-log helper) with the viewing staff member's identity — viewing someone else's private conversation is a distinct, accountable action, not an ordinary part of the messaging surface. A booking with no conversation yet returns 404 rather than silently succeeding with an empty list, since staff shouldn't be the ones creating a conversation that never existed.

## 8. Message reporting

Reuses the generic, already-polymorphic `reports` table (`ReportEntityType.MESSAGE`, existing since Phase 6/7 moderation) rather than a bespoke messages-specific reports table. Reporting requires conversation membership — you can only report a message you were actually allowed to see.

## 9. Client implementations

- **Web**: a `BookingConversation` component embedded directly in the booking detail page (`/bookings/{id}`) — send text/image, load-older pagination, per-message report. A separate `/messages` conversation-list page and `/notifications` history page, both linked from the account page. A minimal `/admin/bookings/{id}/conversation` staff view.
- **Flutter**: a real "Messages" tab (shared by both the customer and artist shells — the backend resolves "the other party" relative to whoever's asking, so one screen serves both roles) listing conversations, and a conversation-detail screen (routed by booking id, since the backend's endpoints are booking-scoped) covering send text/image/report/read-status. Deliberately **not** built this phase: a Flutter notification-history screen (the existing `notification_preferences_screen.dart`, Phase 4/5, already covers preferences) and the staff dispute-review view — both web-only, consistent with this session's recurring "customer/artist-facing surfaces get parity across clients; staff tooling and secondary history screens stay web-only" scope discipline.

## 10. What Phase 14 deliberately does not do

No real push/email provider integration (§4) — foundation only. No reminder scheduler (§3d) — the function exists, nothing calls it automatically. No SMS notifications. No `inquiry`/`support` conversation types (only `booking`). No message editing or deletion (messages are append-only, matching this codebase's audit-trail-style tables). No typing indicators or real-time delivery (polling/refresh-based, no WebSocket layer). No per-message read receipts (§6 — a single read cursor per member). No fine-grained per-notification-type preference toggles beyond the existing coarse email/push/sms switches.

## 11. Related documents

- [booking-lifecycle.md](booking-lifecycle.md) — the booking state machine this phase's alerts and conversation lifecycle attach to
- [profile-and-privacy.md](profile-and-privacy.md) — `user_blocks`/`user_preferences`/`user_devices` foundations this phase finally enforces/consumes
- [artist-verification.md](artist-verification.md) — the audit-log pattern §7 reuses
