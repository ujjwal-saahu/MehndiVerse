# MehndiVerse — Database Relationships

Status: Draft (Phase 2)
Last updated: 2026-07-14

This document describes how the 41 tables in the MehndiVerse schema relate to each other, grouped by domain. Column-level conventions (enum strategy, soft delete, cascades, money) are in [database-schema.md](database-schema.md). Booking status transitions are in [booking-status-rules.md](booking-status-rules.md).

## 1. Users & artists

```mermaid
erDiagram
    USERS ||--o| PROFILES : "has"
    USERS ||--o| USER_PREFERENCES : "has"
    USERS ||--o{ USER_DEVICES : "registers"
    USERS ||--o| ARTIST_PROFILES : "may have (role=artist)"
    ARTIST_PROFILES ||--o{ ARTIST_DOCUMENTS : "submits"
    ARTIST_PROFILES ||--o{ ARTIST_SERVICES : "offers"
    ARTIST_PROFILES ||--o{ ARTIST_AVAILABILITY : "sets"
    ARTIST_PROFILES ||--o{ ARTIST_BLOCKED_DATES : "blocks"
```

* A `user` is the base account row (all roles). `role` (Guest excluded — guests have no row) is enum-constrained: `customer`, `artist`, `moderator`, `administrator`, `super_administrator`. Premium Customer and Verified Artist are **statuses**, not roles — see [user-roles-and-permissions.md](user-roles-and-permissions.md) and §3 below.
* `profiles` and `user_preferences` are 1:1 extensions of `users`, split out to keep auth-critical fields (`users`) separate from public-facing/preference fields. Both cascade-delete with their user.
* `user_devices` is 1:N (a user can register multiple push-notification devices); each `device_token` is globally unique.
* `artist_profiles` is a 1:1 extension of `users` for artist-role accounts. `verification_status` (`pending` → `under_review` → `verified`/`rejected`, or `suspended`) is how "Verified Artist" is represented — there is no separate role value for it.
* `artist_documents`, `artist_services`, `artist_availability`, `artist_blocked_dates` all belong to exactly one `artist_profile` (1:N).

## 2. Design catalog & engagement

```mermaid
erDiagram
    DESIGNS ||--o{ DESIGN_IMAGES : "has"
    DESIGNS }o--o{ CATEGORIES : "design_categories"
    DESIGNS }o--o{ TAGS : "design_tags"
    CATEGORIES ||--o{ CATEGORIES : "parent_category_id (self)"
    ARTIST_PROFILES ||--o{ DESIGNS : "may own"
    USERS ||--o{ LIKES : "likes"
    DESIGNS ||--o{ LIKES : "liked by"
    USERS ||--o{ COMMENTS : "writes"
    DESIGNS ||--o{ COMMENTS : "has"
    COMMENTS ||--o{ COMMENTS : "parent_comment_id (replies)"
    USERS ||--o{ COLLECTIONS : "owns"
    COLLECTIONS ||--o{ COLLECTION_ITEMS : "contains"
    DESIGNS ||--o{ COLLECTION_ITEMS : "saved in"
    USERS ||--o{ FOLLOWS : "follows"
    ARTIST_PROFILES ||--o{ FOLLOWS : "followed by"
```

* `designs.artist_profile_id` is **nullable** — a NULL means a platform/admin-curated design not tied to a specific artist's portfolio.
* `design_categories` and `design_tags` are pure many-to-many join tables with a composite primary key (no synthetic UUID) plus a `created_at` for "when was this tag/category applied."
* `categories.parent_category_id` self-references for a subcategory hierarchy (e.g. "Bridal" → "Bridal — Arabic Style"), nullable for top-level categories.
* `likes` and `follows` are pure join/fact tables (no soft delete — unliking or unfollowing is a real deletion). `collection_items` similarly.
* `comments` supports one level of nesting via `parent_comment_id`; it **is** soft-deleted so a removed parent comment doesn't orphan or corrupt a reply thread.

## 3. Bookings, quotes, and payments

```mermaid
erDiagram
    USERS ||--o{ BOOKINGS : "requests (customer)"
    ARTIST_PROFILES ||--o{ BOOKINGS : "receives"
    ARTIST_SERVICES ||--o{ BOOKINGS : "optionally for"
    DESIGNS ||--o{ BOOKINGS : "optionally inspired by"
    BOOKINGS ||--o{ BOOKING_QUOTES : "has"
    BOOKINGS ||--o{ BOOKING_STATUS_HISTORY : "logs"
    BOOKINGS ||--o{ BOOKING_ATTACHMENTS : "has"
    BOOKINGS ||--o{ PAYMENTS : "collects"
    PAYMENTS ||--o{ REFUNDS : "may have"
    ARTIST_PROFILES ||--o{ PAYOUTS : "receives"
    BOOKINGS ||--o| REVIEWS : "reviewed via"
    BOOKINGS ||--o{ COUPON_REDEMPTIONS : "may apply"
```

* `bookings` is the center of the marketplace transaction. `status` follows the state machine in [booking-status-rules.md](booking-status-rules.md); the row is **never** deleted — cancellation is `status = 'cancelled'`, not a `DELETE`.
* `booking_quotes` is 1:N: a booking can accumulate multiple quotes over time (renegotiation). Only one should be `pending`/`accepted` at a time — that invariant is enforced at the application/service layer in a later phase, not by a DB constraint (documented, not yet code-enforced, per Phase 2 being schema-only).
* `booking_status_history` is an **append-only** audit log: one row per transition, `from_status` nullable for the initial `requested` row.
* `booking_attachments` holds photos/documents shared during a booking (reference images, ID proof for on-location bookings, etc.).
* `payments.booking_id` → `bookings`, `RESTRICT` on delete. A `payment` can have multiple `refunds` (partial refunds). `payouts.booking_id` is nullable because a payout may later aggregate multiple bookings (not modeled yet — out of scope per [feature-scope.md](feature-scope.md), payout automation is Post-MVP).
* `reviews.booking_id` is unique — exactly one review per booking.
* `coupon_redemptions.booking_id` is nullable (a coupon could in principle be redeemed outside a booking context, e.g. a subscription discount — not modeled yet, column exists for the booking case which is the only one wired up now).

## 4. Messaging

```mermaid
erDiagram
    BOOKINGS ||--o| CONVERSATIONS : "may scope"
    CONVERSATIONS ||--o{ CONVERSATION_MEMBERS : "has"
    USERS ||--o{ CONVERSATION_MEMBERS : "participates as"
    CONVERSATIONS ||--o{ MESSAGES : "contains"
    USERS ||--o{ MESSAGES : "sends"
```

* `conversations.booking_id` is nullable — `type` distinguishes `booking` (scoped to a specific booking), `inquiry` (pre-booking question), and `support` (customer/artist ↔ staff).
* `conversation_members` is the join between `conversations` and `users`, carrying a per-conversation `role` label and read-state (`last_read_at`).
* `messages.sender_id` uses `RESTRICT` (a message shouldn't be able to lose its author via cascade); `conversation_id` uses `CASCADE` (deleting a conversation removes its messages — conversations themselves are not currently deletable from the UI, this is a safety net for admin cleanup).

## 5. Subscriptions, reviews, notifications, moderation, coupons, AI, system

```mermaid
erDiagram
    SUBSCRIPTION_PLANS ||--o{ SUBSCRIPTIONS : "purchased as"
    USERS ||--o{ SUBSCRIPTIONS : "holds"
    USERS ||--o{ NOTIFICATIONS : "receives"
    USERS ||--o{ REPORTS : "files"
    USERS ||--o{ COUPONS : "created by (admin)"
    COUPONS ||--o{ COUPON_REDEMPTIONS : "redeemed as"
    USERS ||--o{ PREVIEW_PROJECTS : "creates"
    DESIGNS ||--o{ PREVIEW_PROJECTS : "previewed with"
    USERS ||--o{ AI_GENERATIONS : "triggers (optional)"
    USERS ||--o{ AUDIT_LOGS : "acts as (optional)"
```

* `subscription_plans.target_role` distinguishes Customer (Premium Customer) plans from Artist (visibility-boost) plans, per [feature-scope.md](feature-scope.md#2-post-mvp) — both share one table since the shape (price, billing interval, feature flags) is identical.
* `reports.reported_entity_id` is a **polymorphic reference with no database foreign key** — see [database-schema.md](database-schema.md#8-polymorphic-references). `reported_entity_type` says which table `reported_entity_id` points into (`design`, `comment`, `message`, `user`, `artist_profile`, `review`); the application validates the reference exists at write time.
* `ai_generations.user_id` is nullable to allow logging guest AI usage (rate-limited discovery/preview per [user-roles-and-permissions.md](user-roles-and-permissions.md)) via `guest_session_id` instead.
* `audit_logs.actor_id` is nullable for system-initiated actions (e.g. an automated booking expiry) and `SET NULL` on user deletion — see [database-schema.md](database-schema.md#6-foreign-keys-and-cascade-policy).
* `system_settings` is a flat key/value (JSONB value) store for non-critical runtime configuration, editable by Administrators (`is_public` marks whether a setting is safe to expose to clients).

## 6. Related documents

* [database-schema.md](database-schema.md)
* [booking-status-rules.md](booking-status-rules.md)
* [migration-guidelines.md](migration-guidelines.md)
* [system-architecture.md](system-architecture.md)
