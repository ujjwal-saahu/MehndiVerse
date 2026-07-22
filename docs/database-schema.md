# MehndiVerse — Database Schema Conventions

Status: Draft (Phase 2)
Last updated: 2026-07-14

This document defines the conventions every table in the MehndiVerse schema follows. It complements [database-relationships.md](database-relationships.md) (what the tables mean and how they relate) and [migration-guidelines.md](migration-guidelines.md) (how to change the schema over time). The schema itself lives in `apps/api/app/db/models/` (SQLAlchemy 2.0 declarative models) and is materialized via Alembic migrations in `apps/api/migrations/versions/`.

## 1. Primary keys

Every table uses a UUID v4 primary key, generated server-side by Postgres:

```python
id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
)
```

(`app/db/mixins.py::UUIDPrimaryKeyMixin`.) `gen_random_uuid()` is a Postgres 13+ core function — no extension required. UUIDs avoid leaking row counts/creation order, and let any client (mobile, web, worker) generate a valid ID before an insert if ever needed, without a round-trip.

Join tables with a natural composite key (`design_categories`, `design_tags`) use that composite as the primary key instead of a synthetic UUID — there is no independent identity for "this design is in this category" beyond the pair itself.

## 2. Timestamps

`created_at` / `updated_at` are `TIMESTAMPTZ` (`DateTime(timezone=True)` in SQLAlchemy), defaulting to `now()` server-side. Postgres `timestamptz` always stores the instant in UTC internally regardless of session timezone — that satisfies "UTC timestamps" without the application needing to do anything special. Display/formatting into a local timezone is a client concern.

`updated_at` refreshes via SQLAlchemy's `onupdate=func.now()` for ORM-issued `UPDATE`s. This is an **application-level** guarantee, not a database trigger — a raw SQL `UPDATE` that bypasses the ORM will not refresh it. If a future phase needs a DB-level guarantee (e.g., for updates from a non-Python service), add a trigger then; it isn't needed yet.

Append-only/immutable tables (`booking_status_history`, `audit_logs`, `ai_generations`, `coupon_redemptions`) intentionally have **no** `updated_at` — a row that is never updated shouldn't imply it might be.

## 3. Soft deletion policy

A nullable `deleted_at` column (`app/db/mixins.py::SoftDeleteMixin`) marks a row as soft-deleted without removing it. Applied only where an end-user or moderator action should be reversible/auditable:

| Has soft delete | Reasoning |
|---|---|
| `users`, `profiles` | Account deactivation must be recoverable and not break every FK pointing at the user. |
| `artist_profiles`, `artist_services` | Artists can pause/withdraw a profile or service without losing history. |
| `designs`, `comments`, `collections`, `reviews` | Moderation and user-initiated deletion should leave a trace, not erase content that other rows (likes, collection items, ratings) reference. |
| `messages`, `notifications`, `preview_projects` | User-facing "delete" actions (delete for me, clear notification, remove a preview project) shouldn't destroy the row other participants or audit flows still need. |

**Never soft-deleted** (and never hard-deleted either): `bookings`, `booking_quotes`, `booking_status_history`, `booking_attachments`, `payments`, `refunds`, `payouts`, `audit_logs`, `ai_generations`, `coupon_redemptions`. These are financial or audit records. A booking is "deleted" by transitioning its `status` to `CANCELLED`, never by removing the row — see [booking-status-rules.md](booking-status-rules.md).

Join/log tables (`likes`, `follows`, `collection_items`, `design_categories`, `design_tags`) have no soft delete — removing a like or a tag assignment is a real deletion of a fact with no independent meaning once removed (unliking a design isn't something you'd ever need to "undo" by restoring a row).

## 4. Enum strategy

Every "enum-like" column (`status`, `type`, `role`, ...) is stored as `VARCHAR` with a `CHECK` constraint — **not** a native PostgreSQL `ENUM` type.

**Why not native enums:** altering a PG enum type (renaming or removing a value, as opposed to adding one) requires rebuilding the type, and some of those alterations can't run inside a transaction. A marketplace schema this early changes status vocabularies often. Optimizing for cheap migrations wins over the marginal storage/lookup efficiency of native enums.

**Implementation:** `app/db/enums.py` defines one Python `StrEnum` per column as the single source of truth, and a `check_in(column, enum_cls)` helper that renders the `CHECK` constraint SQL from it:

```python
class BookingStatus(StrEnum):
    REQUESTED = "requested"
    ...

CheckConstraint(check_in("status", BookingStatus), name="status_valid")
```

To add/remove/rename an allowed value: edit the enum in `app/db/enums.py`, then write a migration that drops and recreates the affected `CHECK` constraint (see [migration-guidelines.md](migration-guidelines.md)). The database and the application can never drift because both read from the same enum.

## 5. Monetary values

* All money columns are `NUMERIC(p, s)` (`Numeric` in SQLAlchemy) — **never** floating point. `Numeric(10, 2)` for most amounts, `Numeric(12, 2)` for `payments`/`refunds`/`payouts` (headroom for larger aggregate transactions), `Numeric(10, 4)` for `ai_generations.cost_usd` (sub-cent provider billing).
* Every amount column is paired with an explicit `currency` column (`String(3)`, ISO 4217), with **no default** — the application must supply it. No default avoids silently assuming a currency before a payment provider/region decision is made (still open per [product-requirements.md](product-requirements.md#7-open-questions--decisions-deferred)).
* `CHECK` constraints enforce non-negativity (`>= 0`) or strict positivity (`> 0`) per column, e.g. `payments.amount > 0`, `bookings.deposit_amount >= 0` (nullable — no deposit set yet).

## 6. Foreign keys and cascade policy

Every foreign key sets an explicit `ondelete` — there is no "default" FK in this schema. Three behaviors are used, chosen per relationship:

* **`CASCADE`** — the child row has no meaning without its parent (e.g. `design_images` when a `design` is hard-deleted, `collection_items` when a `collection` is hard-deleted, `artist_availability`/`artist_blocked_dates` when an `artist_profile` is hard-deleted). Since most of these parents are soft-deleted in practice, CASCADE here is a safety net for an actual admin hard-delete, not something that fires during normal moderation.
* **`SET NULL`** — the reference is informational and the child row still means something without it (e.g. `designs.artist_profile_id` if an artist profile is hard-deleted, `audit_logs.actor_id` if a user is hard-deleted, `bookings.cancelled_by`).
* **`RESTRICT`** — the database refuses the delete outright. Used everywhere a delete would otherwise destroy or orphan **financial or audit-relevant** data: every FK from `payments`, `refunds`, `payouts`, `bookings`, `booking_quotes`, `booking_status_history`, `booking_attachments`, `reviews`, `coupons`, `coupon_redemptions` back to `users`/`bookings`/`artist_profiles`/`payments`. You cannot delete a user, artist profile, or booking that has payment or booking history — the application must not expose a hard-delete for those entities at all (soft-delete or status transitions are the only "removal" path where one exists).

`audit_logs.actor_id` is the one deliberate exception inside "audit data": it uses `SET NULL` rather than `RESTRICT`. The goal for audit logs is that the **log row must survive**, not that the user must be undeletable — `SET NULL` achieves that (the row persists, anonymized) without permanently locking every actor's account in place.

## 7. Unique constraints and indexes

* Natural uniqueness is enforced at the database, not just the application: `users.email` (case-insensitively, via a functional unique index on `lower(email)`), `users.phone`, `categories.slug`, `tags.slug`, `payments.provider_payment_id`, `subscriptions.provider_subscription_id`, composite uniqueness for join/preference rows (`uq_likes_user_design`, `uq_follows_follower_artist`, `uq_collection_items_collection_design`, `uq_conversation_members_conv_user`, `uq_coupon_redemptions_coupon_user`, etc.).
* Every foreign key column has an index — Postgres does not create one automatically for FK columns, only for the referenced primary key.
* Frequently-filtered columns are indexed individually: `bookings.status`, `payments.status`, `reports.status`, `audit_logs.action`.

## 8. Polymorphic references

`reports.reported_entity_id` references one of several tables (`design`, `comment`, `message`, `user`, `artist_profile`, `review`) depending on `reports.reported_entity_type`. This is **not** backed by a database foreign key — Postgres has no native polymorphic FK, and simulating one with a trigger or multiple nullable FK columns (one per possible target) was judged not worth the complexity for a moderation-queue table. Integrity for this reference is validated at the application layer when a report is created. See [database-relationships.md](database-relationships.md#reports) for the full rationale.

## 9. Auth boundary

`users.id` is expected to equal the corresponding Supabase Auth `auth.users.id` once the auth integration phase wires real sign-up/sign-in up. There is no FK to `auth.users` because that table lives in Supabase's own `auth` schema, outside this repository's Alembic-managed schema. Supabase Auth owns credentials (password hashes, OAuth tokens, sessions) — nothing password-related is stored in `users`.

## 10. Related documents

* [database-relationships.md](database-relationships.md)
* [booking-status-rules.md](booking-status-rules.md)
* [migration-guidelines.md](migration-guidelines.md)
* [security-baseline.md](security-baseline.md)
