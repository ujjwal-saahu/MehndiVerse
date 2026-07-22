# MehndiVerse — Admin Dashboard (Phase 17)

Status: Implemented (Phase 17)
Last updated: 2026-07-16

Nineteen permission-aware modules covering everything staff need to run the platform day to day — user/artist/design/category/tag management, booking and dispute handling, payment and refund review, the reports queue, review moderation, three brand-new marketing domains (promotional banners, featured collections, notification campaigns), a global audit-log viewer, system settings, and admin-role management. Hosted in the dedicated `apps/admin` workspace, which existed since an early phase as pure "Coming Soon" UI shells (`ComingSoon` component, `docs/design-system.md`) waiting for this phase to fill in.

## 1. Dashboard modules

| Module | Route | View | Edit |
|---|---|---|---|
| Dashboard overview | `/dashboard` | moderator+ | — |
| User management | `/dashboard/users` | moderator+ | admin+ |
| Artist verification | `/dashboard/verification` | moderator+ | admin+ |
| Artist management | `/dashboard/artists` | moderator+ | admin+ |
| Design moderation | `/dashboard/designs` | moderator+ | admin+ |
| Categories | `/dashboard/categories` | moderator+ | admin+ |
| Tags | `/dashboard/tags` | moderator+ | admin+ |
| Bookings | `/dashboard/bookings` | moderator+ | admin+ |
| Payments | `/dashboard/payments` | moderator+ | — (read-only) |
| Refunds | `/dashboard/refunds` | moderator+ | admin+ |
| Reports | `/dashboard/reports` | moderator+ | admin+ |
| Disputes | `/dashboard/disputes` | moderator+ | admin+ |
| Review moderation | `/dashboard/reviews` | moderator+ | admin+ |
| Promotional banners | `/dashboard/banners` | moderator+ | admin+ |
| Featured collections | `/dashboard/featured-collections` | moderator+ | admin+ |
| Notification campaigns | `/dashboard/campaigns` | moderator+ | admin+ |
| Audit log | `/dashboard/audit-log` | admin+ | admin+ |
| System settings | `/dashboard/settings` | super_admin | super_admin |
| Role management | `/dashboard/roles` | super_admin | super_admin |

"View"/"Edit" mirror the `_VIEW_ROLES`/`_EDIT_ROLES` split established in Phase 10's `admin_artist_verification.py` — moderators can see everything (so they can triage and escalate) but only admin/super_admin can act, with system settings and role management raised one tier further to super_admin only.

## 2. Server-side permission checks

Every backend route depends on `require_roles(*_VIEW_ROLES)` or `require_roles(*_EDIT_ROLES)` from `app/api/deps.py` — the same mechanism every prior admin surface uses. The Next.js sidebar (`nav-items.ts`) hides links a role can't use, and `current-staff-user.ts`'s `requireStaffUser()`/`requireEditStaffUser()`/`requireSuperAdminUser()` re-check the role server-side on every page load — but both are UX conveniences, not the boundary. A moderator who bypasses the hidden sidebar link and posts a suspend request directly still gets a 403 from the backend, because the backend never trusts anything the client claims about its own role (see `docs/authentication.md`).

## 3. Search, filters, pagination, and sorting

`app/core/admin_listing.py` is new this phase: offset pagination (`page`/`page_size`, clamped to sane bounds) plus an explicit per-endpoint sort-column allow-list (`resolve_sort_column()` — never a raw client-supplied column name). This is deliberately different from the cursor (keyset) pagination `app/core/pagination.py` already established for public design-gallery feeds: cursor pagination is right for a deep, single-sort-order public feed, but an admin data table needs the opposite — jumping to page N and flipping sort direction on click, which a cursor (tied to one fixed order) can't do without first holding a cursor minted for the old order. Every new list endpoint in this phase (`admin_users.py`, `admin_designs.py`, `admin_bookings.py`, `admin_payments.py`, `admin_reviews.py`, `admin_tags.py`, the three marketing domains, `admin_audit_log.py`) uses it. The two modules that predate this phase and already had cursor pagination (artist verification, the Phase 16 report queue) keep it — Artist Management (§7) reuses the verification queue's cursor endpoint rather than introducing a second, inconsistent pagination style for the same underlying data.

The `DataTable` component (`apps/admin/src/components/table/data-table.tsx`, previously a Phase-4 UI shell with no sorting) now accepts an optional `sortKey` per column; when set, the header becomes a button with a live `aria-sort` attribute. `Pagination` (new) is page-number-based to match, not "load more" — admin lists are bounded, and jumping to a specific page is a real workflow.

## 4. Confirmation for destructive actions

`ConfirmDialog` (new, `role="alertdialog"`) gates every irreversible action with no other safeguard: deleting a tag, a banner, a featured collection, or approving a refund (the point money actually moves). Actions that already require a typed reason (§5) get their confirmation "for free" — typing and submitting a reason *is* the confirmation step, so those don't get a second modal on top.

## 5. Mandatory reasons

`ReasonDialog` (new) is the client-side counterpart to every reason-taking backend schema, all of which use `Field(min_length=1, ...)` — never `str | None`. This phase tightened two pre-existing schemas that were previously optional, since every other moderation action here requires one and leaving these two as the exception was an inconsistency, not a considered choice:

- `RefundRejectRequest.reason` (`app/schemas/payment.py`) — was `str | None`, now mandatory.
- `ReportResolutionRequest.resolution_notes` (`app/schemas/moderation.py`, Phase 16) — was `str | None`, now mandatory.

Both changes were verified against the existing Phase 13/16 test suites, which already always passed a real value — tightening the schema didn't require touching either test file.

Every new mutation that suspends, rejects, moderates, or disputes also calls `record_audit_log()` (§6) with the reason folded into `after_state`, so *why* an action was taken is preserved next to *what* changed.

## 6. Audit logs for privileged changes

`app/services/audit.py::record_audit_log()` (Phase 10) is reused, not reinvented, everywhere this phase writes a privileged change: user suspend/reactivate/role-change, design moderation, booking dispute open/resolve, review moderation, and system-setting upserts. Two pre-existing gaps were closed in the same spirit:

- `admin_users.py::update_user_role()` had no audit entry at all before this phase — the single most privileged action in the system was previously silent. It now logs `user.role_change` with before/after role.
- Refund approve/reject were *already* audited, just via a separate local `_record_audit()` helper inside `app/services/payments/service.py` (financial events don't have an inbound HTTP request the way most admin actions do, so it skips the `ip_address`/`user_agent` capture `record_audit_log()` does) — confirmed during this phase's audit rather than duplicated.

`admin_audit_log.py` (new) is the first *global* viewer — every previous audit-log read was scoped to one artist profile (`admin_artist_verification.py`'s `/audit-log` sub-route). Restricted to admin/super_admin (not moderator): audit entries can expose another staff member's privileged actions, a step above the moderation-queue-style views moderators otherwise get.

## 7. Artist management vs. artist verification

"Artist management" (browsing/acting on any artist regardless of status) and "Artist verification" (the pending-review queue) are two *views* over the same backend endpoint, not two backends. `list_verification_queue()` already accepted a `status_filter` override; Artist Management just defaults it to every status instead of `submitted`/`under_review`, and adds a `search` parameter (by professional/business name) that didn't exist before this phase. One new action, `POST /admin/artists/{id}/reactivate` (`SUSPENDED → APPROVED`, already a valid transition in `ARTIST_VERIFICATION_STAFF_TRANSITIONS`), completes the suspend/reactivate lifecycle the verification module didn't need on its own.

## 8. Dispute management

No customer- or artist-facing "raise a dispute" action exists anywhere in this codebase — `BookingStatus.DISPUTED` was reachable only via direct DB manipulation before this phase. Rather than add a new customer-facing flow (out of scope for an admin-dashboard phase), dispute management is staff-only end to end: `POST /admin/bookings/{id}/dispute` (reason required) moves an eligible booking (`confirmed`/`deposit_pending`/`deposit_paid`/`in_progress`) into `disputed`, and `POST /admin/bookings/{id}/resolve-dispute` (reason required) moves it back out to `completed`/`cancelled`/`refunded` — both going through the existing `transition_booking()` state machine, so a dispute can never bypass the same status-history trail every other transition leaves.

## 9. Review moderation and rating-aggregation consistency

Four actions — `flag`/`unflag`/`remove`/`restore` — cover both `Review.is_flagged` (mark for attention without hiding) and soft-delete (`Review.deleted_at`, via `SoftDeleteMixin`). Every action re-runs `recompute_artist_rating()` (Phase 16) afterward, even `flag`/`unflag` which don't change what counts toward the aggregate — cheaper to always recompute than to special-case which actions need it, and it guarantees `ArtistProfile.rating_average`/`rating_count` can never drift from what a moderator's remove/restore action actually did.

## 10. New marketing domains

Promotional banners, featured collections, and notification campaigns had zero prior schema — three new tables (`promo_banners`, `featured_collections`/`featured_collection_items`, `notification_campaigns`; see migration `7a448a982206`) and a full admin CRUD surface each, in `app/db/models/promotions.py` (distinct from the pre-existing, still-unused `app/db/models/marketing.py::Coupon`/`CouponRedemption`, a Phase-2 scaffold this phase doesn't touch).

- **Banners**: plain CRUD plus an active/inactive toggle. `starts_at`/`ends_at` are optional scheduling bounds recorded but not yet enforced — no public banner-serving endpoint exists yet; combining them into an "is this live right now" check is a future phase's concern.
- **Featured collections**: a staff-curated group of designs for homepage merchandising, deliberately a separate table from the pre-existing user-owned `collections` (`app/api/routes/collections.py`) — this one has no owning user and is never private.
- **Notification campaigns**: drafted, then sent once. Sending fans out synchronously via the existing per-user `notify_user()` to every active user matching `target_role` (or everyone) — the same "foundation, not a scheduler" caveat as the Phase 14 booking-reminder function, since no task-queue infrastructure exists in this environment. `recipient_count` records how many notifications the send actually produced.

None of the three gets a public-facing consumption endpoint this phase (no homepage banner carousel, no featured-designs section) — that's an intentional scope boundary (§12), not an oversight.

## 11. Super-admin-only modules and self-escalation prevention

System settings and role management are gated to super_admin only, both server-side (`require_roles("super_admin")`) and via the dashboard nav/page guard (`requireSuperAdminUser()`). This sits alongside, and doesn't replace, the pre-existing tiered role-grant system (`app/core/authz.py::GRANTABLE_ROLES_BY_GRANTOR`, predates this phase): admin can still grant customer/artist/moderator directly (day-to-day account operations), but only super_admin can grant admin/super_admin, and **nobody can change their own role** (`user_id == current.user.id` check in `update_user_role()`, unconditional regardless of caller's role) — the concrete mechanism behind "prevent administrators from escalating their own permissions." An admin attempting to mint another admin, or a super_admin attempting to promote themselves, both get 403 today exactly as they did before this phase; Phase 17 didn't need to change that logic, only build a UI in front of it and restrict which staff tier sees that UI at all.

## 12. What Phase 17 deliberately does not do

No public consumption endpoints for the three new marketing domains (§10) — admin-side CRUD only. No banner/featured-collection scheduling logic beyond recording the dates. No bulk moderation actions (every action targets one row at a time). No design-picker UI for adding a design to a featured collection — the admin pastes a design ID (a future phase's UX concern, not a capability gap). No customer/artist-facing "raise a dispute" flow (§8) — dispute management is entirely staff-initiated. No notification-campaign scheduling ("send at a future time") — a campaign sends immediately when triggered. No Flutter admin UI — staff tooling has been web-only since Phase 14 (`docs/booking-messaging.md#9`), and this phase's audience is exclusively staff.

## 13. Related documents

- `docs/artist-verification.md` — the `_VIEW_STAFF_ROLES`/`_EDIT_STAFF_ROLES` RBAC split and cursor-paginated-queue pattern this phase's new list endpoints follow (for offset pagination) or directly reuse (for artist management, §7)
- `docs/community-and-trust.md` — the Phase 16 report queue and shared `create_report()`/blocking-enforcement work the Reports module surfaces, and the rating-aggregation discipline §9 extends
- `docs/payments.md` — the refund approve/reject flow and financial audit-event pattern (`_record_audit()`) this phase's Payments/Refunds modules surface without duplicating
- `docs/booking-lifecycle.md` — the booking state machine (`transition_booking()`, `BOOKING_STATUS_TRANSITIONS`) dispute management (§8) drives through rather than around
- `docs/authentication.md` — the effective-role computation and self-escalation guards (§11) this phase's role-management UI sits in front of
